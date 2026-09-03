from __future__ import annotations

from html import escape

from .frontend_identifier_generation import build_known_player_handle_v1
from .frontend_profile_contracts import LocalFrontendProfileV1
from .frontend_profile_operations import FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE
from .managed_item_contracts import ManagedCategoryViewV1
from .profile_driven_creation import FRIENDLY_GAME_PLATFORMS
from .translation_catalog import translate_frontend_message_v1


def _t(locale: str, key: str, **values: object) -> str:
    return escape(translate_frontend_message_v1(locale, key, **values))


def _default_player_ids(profile: LocalFrontendProfileV1 | None) -> tuple[str, ...]:
    if profile is None:
        return ()
    return tuple(
        dict.fromkeys(
            player_id
            for player_id in (
                profile.own_player_id,
                profile.preferred_perspective_player_id,
            )
            if player_id is not None
        )
    )


def _player_fields(
    profile: LocalFrontendProfileV1 | None,
    *,
    index: int,
    seat_key: str,
    locale: str,
) -> str:
    default_ids = _default_player_ids(profile)
    default_player_id = default_ids[index - 1] if index <= len(default_ids) else None
    options = [f'<option value="">{_t(locale, "creation.common.no_saved_player")}</option>']
    if profile is not None:
        options.extend(
            f'<option value="{build_known_player_handle_v1(player.player_id)}"'
            f"{' selected' if player.player_id == default_player_id else ''}>"
            f"{escape(player.display_name)}</option>"
            for player in profile.known_players
        )
    return (
        f"<fieldset><legend>{_t(locale, f'creation.seat.{seat_key}')}</legend>"
        f"<p>{_t(locale, 'creation.common.player_choice_help')}</p>"
        f"<label>{_t(locale, 'creation.common.known_player')}"
        f'<select name="player_{index}_handle">{"".join(options)}</select></label>'
        f"<label>{_t(locale, 'creation.common.new_player_name')}"
        f'<input name="player_{index}_name" maxlength="120"></label></fieldset>'
    )


def _players(
    profile: LocalFrontendProfileV1 | None,
    locale: str,
) -> str:
    return "".join(
        _player_fields(profile, index=index, seat_key=seat, locale=locale)
        for index, seat in enumerate(("forehand", "middlehand", "rearhand"), start=1)
    )


def _perspective_options(
    profile: LocalFrontendProfileV1 | None,
    locale: str,
    *,
    optional: bool,
) -> str:
    preferred = None if profile is None else profile.preferred_perspective_player_id
    default_ids = _default_player_ids(profile)
    preferred_index = (
        None if preferred is None or preferred not in default_ids else default_ids.index(preferred)
    )
    options = (
        f'<option value="">{_t(locale, "creation.common.no_perspective")}</option>'
        if optional
        else f'<option value="">{_t(locale, "creation.common.choose_perspective")}</option>'
    )
    return options + "".join(
        f'<option value="{seat}"'
        f"{' selected' if preferred_index == index - 1 else ''}>"
        f"{_t(locale, f'creation.seat.{seat}')}</option>"
        for index, seat in enumerate(("forehand", "middlehand", "rearhand"), start=1)
    )


def _save_controls(locale: str) -> str:
    return (
        f"<p>{_t(locale, 'creation.common.local_save_help')}</p>"
        f"<label>{_t(locale, 'creation.common.save_players')}"
        '<select name="save_players"><option value="true" selected>'
        f'{_t(locale, "common.answer.yes")}</option><option value="false">'
        f"{_t(locale, 'common.answer.no')}</option></select></label>"
        f"<label>{_t(locale, 'creation.common.save_preferences')}"
        '<select name="save_preferences"><option value="false" selected>'
        f'{_t(locale, "common.answer.no")}</option><option value="true">'
        f"{_t(locale, 'common.answer.yes')}</option></select></label>"
    )


def _profile_generation(generation: int) -> str:
    return f'<input type="hidden" name="profile_generation" value="{generation}">'


def render_profile_driven_session_creation_v1(
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    locale: str,
) -> str:
    return (
        '<section class="panel friendly-create" aria-labelledby="session-create-heading">'
        f'<h2 id="session-create-heading">{_t(locale, "creation.session.heading")}</h2>'
        '<form method="post" action="/sessions/create" class="form-grid">'
        + _profile_generation(profile_generation)
        + f"<label>{_t(locale, 'creation.session.name')} "
        '<input name="game_name" maxlength="160" required></label>'
        f"<fieldset><legend>{_t(locale, 'creation.session.recording_mode')}</legend>"
        f'<label><input type="radio" name="capture_mode" value="live" checked> '
        f"{_t(locale, 'creation.session.during')}</label>"
        f"<p>{_t(locale, 'creation.session.during_help')}</p>"
        f'<label><input type="radio" name="capture_mode" value="retrospective"> '
        f"{_t(locale, 'creation.session.after')}</label>"
        f"<p>{_t(locale, 'creation.session.after_help')}</p></fieldset>"
        + _players(profile, locale)
        + f"<label>{_t(locale, 'creation.session.perspective')}"
        f'<select name="perspective_seat">{_perspective_options(profile, locale, optional=True)}'
        "</select></label>"
        + _save_controls(locale)
        + f'<button type="submit">{_t(locale, "creation.session.action")}</button>'
        "</form></section>"
    )


def _platform_options(
    profile: LocalFrontendProfileV1 | None,
    locale: str,
) -> str:
    preferred = None if profile is None else profile.preferred_game_platform
    values = tuple(
        (choice, product_value, choice) for choice, product_value in FRIENDLY_GAME_PLATFORMS
    ) + (("custom", None, "custom"),)
    known_values = {product_value for _choice, product_value in FRIENDLY_GAME_PLATFORMS}
    selected_choice = next(
        (value for value, machine, _key in values if machine == preferred),
        "custom" if preferred is not None and preferred not in known_values else None,
    )
    return "".join(
        f'<option value="{value}"'
        f"{' selected' if value == selected_choice else ''}>"
        f"{_t(locale, f'creation.platform.{key}')}</option>"
        for value, _machine, key in values
    )


def render_profile_driven_match_creation_v1(
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    locale: str,
) -> str:
    advanced_open = (
        " open"
        if profile is not None and profile.interface_preferences.advanced_settings_expanded
        else ""
    )
    preferred_platform = None if profile is None else profile.preferred_game_platform
    known_platforms = {value for _choice, value in FRIENDLY_GAME_PLATFORMS}
    custom_platform = (
        preferred_platform
        if preferred_platform is not None and preferred_platform not in known_platforms
        else ""
    )
    platform_ids = "".join(
        f"<label>{_t(locale, 'creation.advanced.player_platform_id', seat=seat_label)}"
        f'<input name="player_{index}_platform_id" maxlength="255"></label>'
        for index, seat_label in enumerate(
            (
                _t(locale, f"creation.seat.{seat}")
                for seat in ("forehand", "middlehand", "rearhand")
            ),
            start=1,
        )
    )
    escaped_custom_platform = escape(custom_platform, quote=True)
    perspective_options = _perspective_options(profile, locale, optional=False)
    return (
        '<section class="panel friendly-create" aria-labelledby="match-create-heading">'
        f'<h2 id="match-create-heading">{_t(locale, "creation.match.heading")}</h2>'
        '<form method="post" action="/matches/api/v1/create" class="form-grid">'
        + _profile_generation(profile_generation)
        + f"<label>{_t(locale, 'creation.match.title')} "
        '<input name="match_title" maxlength="160" required></label>'
        f"<label>{_t(locale, 'creation.match.date')} "
        '<input type="date" name="played_date"></label>'
        f'<label>{_t(locale, "creation.match.platform")}<select name="platform_choice">'
        f"{_platform_options(profile, locale)}</select></label>"
        f'<label class="custom-platform-field">{_t(locale, "creation.match.custom_platform")} '
        f'<input name="custom_platform" maxlength="120" '
        f'value="{escaped_custom_platform}"></label>'
        f"<p><strong>{_t(locale, 'creation.match.format')}</strong>: "
        f"{_t(locale, 'creation.match.format_value')}</p>"
        + _players(profile, locale)
        + f"<label>{_t(locale, 'creation.match.perspective')}"
        f'<select name="perspective_seat" required>{perspective_options}'
        "</select></label>"
        f"<label>{_t(locale, 'creation.match.source_url')} "
        '<input type="url" name="source_url" maxlength="2048"></label>'
        + _save_controls(locale)
        + f'<details class="advanced-settings"{advanced_open}><summary>'
        f"{_t(locale, 'creation.advanced.heading')}</summary>"
        f"<p>{_t(locale, 'creation.advanced.help')}</p>"
        f"<label>{_t(locale, 'creation.advanced.external_match_id')} "
        '<input name="external_match_id"></label>'
        f"<small>{_t(locale, 'creation.advanced.external_match_id_help')}</small>"
        + platform_ids
        + f"<small>{_t(locale, 'creation.advanced.player_platform_id_help')}</small>"
        + f'<label>{_t(locale, "creation.advanced.source_kind")}<select name="source_kind">'
        f'<option value="">{_t(locale, "creation.advanced.source_auto")}</option>'
        f'<option value="youtube_video">{_t(locale, "creation.advanced.source_youtube")}</option>'
        f'<option value="other_video">{_t(locale, "creation.advanced.source_other")}</option>'
        '<option value="manual_observation">'
        f"{_t(locale, 'creation.advanced.source_manual')}</option>"
        "</select></label>"
        f"<small>{_t(locale, 'creation.advanced.source_kind_help')}</small>"
        f"<label>{_t(locale, 'creation.advanced.source_title')} "
        '<input name="source_title" maxlength="160"></label>'
        f"<small>{_t(locale, 'creation.advanced.source_title_help')}</small>"
        f"<label>{_t(locale, 'creation.advanced.played_at')} "
        '<input name="played_at" placeholder="2026-09-03T19:30:00+02:00"></label>'
        f"<p>{_t(locale, 'creation.advanced.played_at_help')}</p>"
        '<div class="media-source-fields">'
        f"<label>{_t(locale, 'creation.advanced.source_channel')} "
        '<input name="source_channel_name" maxlength="160"></label>'
        f"<small>{_t(locale, 'creation.advanced.source_channel_help')}</small>"
        f"<label>{_t(locale, 'creation.advanced.timecode_start')} "
        '<input name="match_timecode_start" placeholder="01:02:03"></label>'
        f"<label>{_t(locale, 'creation.advanced.timecode_end')} "
        '<input name="match_timecode_end" placeholder="02:03:04"></label>'
        f"<small>{_t(locale, 'creation.advanced.timecode_help')}</small>"
        "</div>"
        "</details>"
        f'<button type="submit">{_t(locale, "creation.match.action")}</button>'
        "</form></section>"
    )


def render_profile_driven_learning_creation_v1(
    *,
    profile_generation: int,
    locale: str,
) -> str:
    return (
        '<section class="panel friendly-create" aria-labelledby="learning-create-heading">'
        f'<h2 id="learning-create-heading">{_t(locale, "creation.learning.heading")}</h2>'
        '<form method="post" action="/learning/create" class="form-grid">'
        + _profile_generation(profile_generation)
        + f"<label>{_t(locale, 'creation.learning.name')} "
        '<input name="collection_name" maxlength="160" required></label>'
        f'<button type="submit">{_t(locale, "creation.learning.action")}</button>'
        "</form></section>"
    )


def _managed_label_form(
    item,
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    locale: str,
) -> str:
    if item.status == "invalid" or item.semantic_product_id is None:
        return ""
    existing = next(
        (
            label
            for label in (() if profile is None else profile.managed_item_display_labels)
            if label.family == item.family and label.product_id == item.semantic_product_id
        ),
        None,
    )
    if existing is not None:
        display_name = existing.display_name
    elif item.family == "sessions" and item.display_label is not None:
        display_name = translate_frontend_message_v1(
            locale,
            "creation.managed.fallback_session",
            players=item.display_label.removeprefix("Session: "),
        )
    elif item.family == "corpora" and item.display_label is not None:
        display_name = translate_frontend_message_v1(
            locale,
            "creation.managed.fallback_learning",
        )
    else:
        display_name = item.display_label or ""
    played_date = "" if existing is None or existing.played_date is None else existing.played_date
    route_family = "learning" if item.family == "corpora" else item.family
    date_control = (
        f"<label>{_t(locale, 'creation.managed.played_date')} "
        f'<input type="date" name="played_date" value="{escape(played_date, quote=True)}"></label>'
        if item.family == "matches"
        else '<input type="hidden" name="played_date" value="">'
    )
    return (
        '<details class="managed-label-editor"><summary>'
        f"{_t(locale, 'creation.managed.edit_label')}</summary>"
        f'<form method="post" action="{FRONTEND_PROFILE_MANAGED_LABEL_ACTION_ROUTE}">'
        f'<input type="hidden" name="managed_family" value="{item.family}">'
        f'<input type="hidden" name="managed_handle" value="{item.handle}">'
        f'<input type="hidden" name="managed_generation" value="{item.discovery_generation}">'
        f'<input type="hidden" name="profile_generation" value="{profile_generation}">'
        f'<input type="hidden" name="return_to" value="/{route_family}">'
        f"<label>{_t(locale, 'creation.managed.display_name')} "
        f'<input name="display_name" maxlength="160" required '
        f'value="{escape(display_name, quote=True)}"></label>'
        f'{date_control}<button type="submit">'
        f"{_t(locale, 'creation.managed.save_label')}</button></form></details>"
    )


def _managed_item_card(
    item,
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    locale: str,
) -> str:
    profile_label = next(
        (
            value
            for value in (() if profile is None else profile.managed_item_display_labels)
            if value.family == item.family and value.product_id == item.semantic_product_id
        ),
        None,
    )
    if profile_label is not None:
        label = escape(profile_label.display_name)
    elif item.family == "sessions" and item.display_label is not None:
        players = item.display_label.removeprefix("Session: ")
        label = _t(locale, "creation.managed.fallback_session", players=players)
    elif item.family == "corpora" and item.display_label is not None:
        label = _t(locale, "creation.managed.fallback_learning")
    else:
        label = escape(item.display_label) if item.display_label else _t(
            locale,
            "creation.managed.invalid",
        )
    route_family = "learning" if item.family == "corpora" else item.family
    action = ""
    if item.status == "available":
        action_key = "creation.managed.reopen" if item.active else "creation.managed.open"
        action = (
            f'<form method="post" action="/{route_family}/open">'
            f'<input type="hidden" name="handle" value="{escape(item.handle, quote=True)}">'
            f'<input type="hidden" name="generation" value="{item.discovery_generation}">'
            f'<button type="submit">{_t(locale, action_key)}</button>'
            "</form>"
        )
    revision = (
        ""
        if item.revision is None
        else (
            f"<dl><dt>{_t(locale, 'creation.managed.revision')}</dt>"
            f"<dd>{item.revision}</dd></dl>"
        )
    )
    played_date = (
        ""
        if profile_label is None or profile_label.played_date is None
        else (
            f'<p>{_t(locale, "creation.managed.played_date_value")}: '
            f'<time datetime="{profile_label.played_date}">'
            f"{profile_label.played_date}</time></p>"
        )
    )
    status_label = _t(locale, f"creation.managed.status.{item.status}")
    label_editor = _managed_label_form(
        item,
        profile=profile,
        profile_generation=profile_generation,
        locale=locale,
    )
    return (
        f'<article class="managed-item status-{escape(item.status)}"><h3>{label}</h3>'
        f"<p>{_t(locale, 'creation.managed.status')}: {status_label}</p>"
        f"{played_date}{revision}{action}"
        f"{label_editor}"
        "</article>"
    )


def _import_form(family: str, locale: str) -> str:
    if family == "corpora":
        return ""
    file_field = "session_file" if family == "sessions" else "workspace_file"
    return (
        '<details class="secondary-action"><summary>'
        f"{_t(locale, 'creation.import.heading')}</summary>"
        f'<form method="post" action="/{family}/import" enctype="multipart/form-data">'
        f"<label>{_t(locale, 'creation.import.file')} "
        f'<input type="file" name="{file_field}" accept="application/json,.json" required></label>'
        f'<button type="submit">{_t(locale, "creation.import.action")}</button></form></details>'
    )


def render_friendly_managed_category_landing_v1(
    view: ManagedCategoryViewV1,
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    locale: str,
) -> str:
    if type(view) is not ManagedCategoryViewV1:
        raise ValueError("view must be an exact managed category view.")
    create = (
        render_profile_driven_session_creation_v1(
            profile=profile,
            profile_generation=profile_generation,
            locale=locale,
        )
        if view.family == "sessions"
        else (
            '<section class="panel friendly-create"><h2>'
            f"{_t(locale, 'creation.match.heading')}</h2><p>"
            f'{_t(locale, "creation.match.introduction")}</p><p><a class="button-link" '
            f'href="/matches/new">{_t(locale, "creation.match.action")}</a></p></section>'
        )
        if view.family == "matches"
        else render_profile_driven_learning_creation_v1(
            profile_generation=profile_generation,
            locale=locale,
        )
    )
    cards = "".join(
        _managed_item_card(
            item,
            profile=profile,
            profile_generation=profile_generation,
            locale=locale,
        )
        for item in view.items
    )
    empty_items = f"<p>{_t(locale, 'creation.managed.empty')}</p>"
    managed = (
        '<section aria-labelledby="managed-items-heading"><h2 id="managed-items-heading">'
        f"{_t(locale, f'creation.managed.heading.{view.family}')}</h2>"
        f'<div class="managed-item-grid">{cards or empty_items}</div>'
        "</section>"
    )
    limit = (
        f'<p class="notice warning">{_t(locale, "creation.managed.limit")}</p>'
        if view.candidate_limit_reached
        else ""
    )
    return (
        '<section class="managed-landing">'
        f"{create}{limit}{managed}{_import_form(view.family, locale)}</section>"
    )
