from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from urllib.parse import urlsplit

import skatmind.api.v1.session as session_api
from skatmind.rfc3339 import parse_rfc3339_datetime

from .frontend_identifier_generation import (
    generate_frontend_corpus_id_v1,
    generate_frontend_match_id_v1,
    generate_frontend_player_id_v1,
    generate_frontend_session_id_v1,
)
from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_contracts import LocalFrontendProfileV1
from .profile_player_contracts import (
    MAX_KNOWN_PLAYERS,
    MAX_MANAGED_ITEM_DISPLAY_LABELS,
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
    normalize_player_display_name_v1,
)
from .profile_player_operations import resolve_known_player_handle_v1

FRIENDLY_GAME_PLATFORMS = (
    ("euroskat", "EuroSkat"),
    ("in_person", "In-person game"),
    ("other_online", "Other online platform"),
    ("unknown", "Unknown"),
)
FRIENDLY_GAME_PLATFORM_VALUES = tuple(
    choice for choice, _product_value in FRIENDLY_GAME_PLATFORMS
) + ("custom",)
PROFILE_DRIVEN_SESSION_CREATE_FIELDS = (
    "game_name",
    "capture_mode",
    "player_1_handle",
    "player_1_name",
    "player_2_handle",
    "player_2_name",
    "player_3_handle",
    "player_3_name",
    "perspective_seat",
    "save_players",
    "save_preferences",
    "profile_generation",
)
PROFILE_DRIVEN_MATCH_CREATE_FIELDS = (
    "match_title",
    "played_date",
    "platform_choice",
    "custom_platform",
    "player_1_handle",
    "player_1_name",
    "player_2_handle",
    "player_2_name",
    "player_3_handle",
    "player_3_name",
    "perspective_seat",
    "source_url",
    "external_match_id",
    "player_1_platform_id",
    "player_2_platform_id",
    "player_3_platform_id",
    "source_kind",
    "source_title",
    "source_channel_name",
    "played_at",
    "match_timecode_start",
    "match_timecode_end",
    "save_players",
    "save_preferences",
    "profile_generation",
)
PROFILE_DRIVEN_LEARNING_CREATE_FIELDS = (
    "collection_name",
    "profile_generation",
)

_GAME_PLATFORM_BY_CHOICE = dict(FRIENDLY_GAME_PLATFORMS)
_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
_SEATS = ("forehand", "middlehand", "rearhand")


@dataclass(frozen=True, slots=True)
class PreparedProfileDrivenSessionCreationV1:
    session_id: str
    players: tuple[session_api.SessionPlayerV1, ...]
    capture_mode: str
    local_player_id: str | None
    profile_document: LocalFrontendProfileV1 | None
    expected_profile_generation: int


@dataclass(frozen=True, slots=True)
class PreparedProfileDrivenMatchCreationV1:
    match_id: str
    product_values: Mapping[str, str]
    profile_document: LocalFrontendProfileV1 | None
    expected_profile_generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.product_values, MappingProxyType):
            raise ValueError("product_values must be one immutable mapping.")


@dataclass(frozen=True, slots=True)
class PreparedProfileDrivenLearningCreationV1:
    corpus_id: str
    profile_document: LocalFrontendProfileV1 | None
    expected_profile_generation: int


@dataclass(frozen=True, slots=True)
class _SelectedPlayerV1:
    known_player: KnownPlayerV1 | None
    display_name: str
    field_key: str


class ProfileDrivenCreationFieldError(ValueError):
    def __init__(self, field_key: str, message: str) -> None:
        super().__init__(message)
        self.field_key = field_key


def _require_generation(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("expected_profile_generation must be a non-negative integer.")
    return value


def _checkbox(values: Mapping[str, str], name: str) -> bool:
    value = values.get(name, "")
    if value in {"", "off", "false"}:
        return False
    if value in {"on", "true"}:
        return True
    raise ValueError(f"{name} must be one explicit checkbox value.")


def _trimmed(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "")
    if type(value) is not str:
        raise ValueError(f"{name} must be text.")
    return value.strip()


def _validate_label(
    display_name: str,
    *,
    field_key: str,
    family: str,
    played_date: str | None = None,
) -> None:
    try:
        ManagedItemDisplayLabelV1(
            family=family,
            product_id="pending-product",
            display_name=display_name,
            played_date=played_date,
        )
    except ValueError as exc:
        raise ProfileDrivenCreationFieldError(field_key, str(exc)) from exc


def _select_players(
    values: Mapping[str, str],
    profile: LocalFrontendProfileV1 | None,
) -> tuple[_SelectedPlayerV1, ...]:
    selected: list[_SelectedPlayerV1] = []
    known_ids: list[str] = []
    for index in range(1, 4):
        handle = _trimmed(values, f"player_{index}_handle")
        display_name = _trimmed(values, f"player_{index}_name")
        if bool(handle) == bool(display_name):
            field_key = f"player_{index}_{'name' if handle else 'handle'}"
            raise ProfileDrivenCreationFieldError(
                field_key,
                "Each seat requires either one known Player or one new name.",
            )
        if handle:
            try:
                player = resolve_known_player_handle_v1(profile, handle)
            except ValueError as exc:
                raise ProfileDrivenCreationFieldError(
                    f"player_{index}_handle",
                    str(exc),
                ) from exc
            selected.append(
                _SelectedPlayerV1(player, player.display_name, f"player_{index}_handle")
            )
            known_ids.append(player.player_id)
        else:
            try:
                normalize_player_display_name_v1(display_name)
            except ValueError as exc:
                raise ProfileDrivenCreationFieldError(
                    f"player_{index}_name",
                    str(exc),
                ) from exc
            selected.append(_SelectedPlayerV1(None, display_name, f"player_{index}_name"))
    if len(known_ids) != len(set(known_ids)):
        repeated = next(
            player
            for index, player in enumerate(selected)
            if player.known_player is not None
            and any(
                earlier.known_player == player.known_player for earlier in selected[:index]
            )
        )
        raise ProfileDrivenCreationFieldError(
            repeated.field_key,
            "The same known Player cannot occupy two seats.",
        )
    normalized_names: list[str] = []
    for player in selected:
        normalized = normalize_player_display_name_v1(player.display_name)
        if normalized in normalized_names:
            raise ProfileDrivenCreationFieldError(
                player.field_key,
                "Each seat requires a distinct Player display name; duplicate new Player "
                "names and saved/new duplicates are not allowed.",
            )
        normalized_names.append(normalized)
    return tuple(selected)


def _materialize_players(
    selected: tuple[_SelectedPlayerV1, ...],
    *,
    profile: LocalFrontendProfileV1 | None,
    platform: str | None,
    platform_ids: tuple[str, str, str],
    entropy_source: Callable[[int], bytes],
) -> tuple[tuple[KnownPlayerV1, ...], tuple[str, ...], tuple[str | None, ...]]:
    existing_ids = [
        player.player_id for player in (() if profile is None else profile.known_players)
    ]
    new_players: list[KnownPlayerV1] = []
    player_ids: list[str] = []
    product_platform_ids: list[str | None] = []
    for selected_player, submitted_platform_id in zip(
        selected,
        platform_ids,
        strict=True,
    ):
        if selected_player.known_player is None:
            player_id = generate_frontend_player_id_v1(
                existing_ids=tuple(existing_ids),
                entropy_source=entropy_source,
            )
            existing_ids.append(player_id)
            platform_values = (
                ()
                if not submitted_platform_id or platform is None
                else (KnownPlayerPlatformIdV1(platform, submitted_platform_id),)
            )
            player = KnownPlayerV1(
                player_id=player_id,
                display_name=selected_player.display_name,
                aliases=(),
                platform_player_ids=platform_values,
            )
            new_players.append(player)
        else:
            player = selected_player.known_player
        player_ids.append(player.player_id)
        product_platform_ids.append(submitted_platform_id or None)
    return tuple(new_players), tuple(player_ids), tuple(product_platform_ids)


def _profile_with_creation(
    profile: LocalFrontendProfileV1 | None,
    *,
    new_players: tuple[KnownPlayerV1, ...],
    save_players: bool,
    preferred_perspective_player_id: str | None,
    save_perspective: bool,
    preferred_game_platform: str | None,
    save_platform: bool,
    label: ManagedItemDisplayLabelV1,
) -> LocalFrontendProfileV1 | None:
    known_players = () if profile is None else profile.known_players
    if save_players:
        if len(known_players) + len(new_players) > MAX_KNOWN_PLAYERS:
            return None
        known_players = (*known_players, *new_players)
    labels = () if profile is None else profile.managed_item_display_labels
    label_key = (label.family, label.product_id)
    labels = tuple(value for value in labels if (value.family, value.product_id) != label_key) + (
        label,
    )
    if len(labels) > MAX_MANAGED_ITEM_DISPLAY_LABELS:
        return None
    return build_local_frontend_profile_v1(
        revision=0 if profile is None else profile.revision + 1,
        language=None if profile is None else profile.language,
        interface_preferences=(
            build_local_frontend_profile_v1().interface_preferences
            if profile is None
            else profile.interface_preferences
        ),
        own_player_id=None if profile is None else profile.own_player_id,
        known_players=known_players,
        preferred_perspective_player_id=(
            preferred_perspective_player_id
            if save_perspective
            else None
            if profile is None
            else profile.preferred_perspective_player_id
        ),
        preferred_game_platform=(
            preferred_game_platform
            if save_platform
            else None
            if profile is None
            else profile.preferred_game_platform
        ),
        workflow_preferences=(
            build_local_frontend_profile_v1().workflow_preferences
            if profile is None
            else profile.workflow_preferences
        ),
        managed_item_display_labels=labels,
    )


def prepare_profile_driven_session_creation_v1(
    values: Mapping[str, str],
    *,
    profile: LocalFrontendProfileV1 | None,
    expected_profile_generation: int,
    existing_session_ids: tuple[str, ...],
    entropy_source: Callable[[int], bytes],
) -> PreparedProfileDrivenSessionCreationV1:
    generation = _require_generation(expected_profile_generation)
    game_name = _trimmed(values, "game_name")
    _validate_label(game_name, field_key="game_name", family="sessions")
    capture_mode = _trimmed(values, "capture_mode")
    if capture_mode not in {"live", "retrospective"}:
        raise ProfileDrivenCreationFieldError(
            "capture_mode",
            "Recording mode must be During play or After the game.",
        )
    selected = _select_players(values, profile)
    perspective_seat = _trimmed(values, "perspective_seat")
    if perspective_seat not in {"", *_SEATS}:
        raise ProfileDrivenCreationFieldError(
            "perspective_seat",
            "Perspective must identify one visible seat.",
        )
    if capture_mode == "live" and not perspective_seat:
        raise ProfileDrivenCreationFieldError(
            "perspective_seat",
            "During-play recording requires one perspective seat.",
        )
    save_players = _checkbox(values, "save_players")
    save_preferences = _checkbox(values, "save_preferences")
    perspective_index = None if not perspective_seat else _SEATS.index(perspective_seat)
    if (
        save_preferences
        and perspective_index is not None
        and selected[perspective_index].known_player is None
        and not save_players
    ):
        raise ProfileDrivenCreationFieldError(
            "save_preferences",
            "Saving a new preferred perspective also requires saving Players.",
        )

    new_players, player_ids, _platform_ids = _materialize_players(
        selected,
        profile=profile,
        platform=None,
        platform_ids=("", "", ""),
        entropy_source=entropy_source,
    )
    players = tuple(
        session_api.SessionPlayerV1(
            player_id=player_id,
            player_label=selected_player.display_name,
            seat=seat,
        )
        for seat, selected_player, player_id in zip(
            _SEATS,
            selected,
            player_ids,
            strict=True,
        )
    )
    session_id = generate_frontend_session_id_v1(
        existing_ids=existing_session_ids,
        entropy_source=entropy_source,
    )
    local_player_id = None if perspective_index is None else player_ids[perspective_index]
    profile_document = _profile_with_creation(
        profile,
        new_players=new_players,
        save_players=save_players,
        preferred_perspective_player_id=local_player_id,
        save_perspective=save_preferences,
        preferred_game_platform=None,
        save_platform=False,
        label=ManagedItemDisplayLabelV1(
            "sessions",
            session_id,
            game_name,
        ),
    )
    return PreparedProfileDrivenSessionCreationV1(
        session_id=session_id,
        players=players,
        capture_mode=capture_mode,
        local_player_id=local_player_id,
        profile_document=profile_document,
        expected_profile_generation=generation,
    )


def resolve_friendly_game_platform_v1(choice: str, custom_platform: str) -> str:
    if type(choice) is not str or type(custom_platform) is not str:
        raise ValueError("Platform selection must contain text.")
    choice = choice.strip()
    custom_platform = custom_platform.strip()
    if choice not in FRIENDLY_GAME_PLATFORM_VALUES:
        raise ValueError("Platform must be one friendly supported choice.")
    if choice == "custom":
        KnownPlayerPlatformIdV1(custom_platform, "validation-only")
        return custom_platform
    return _GAME_PLATFORM_BY_CHOICE[choice]


def _friendly_platform(values: Mapping[str, str]) -> str:
    choice = _trimmed(values, "platform_choice")
    try:
        return resolve_friendly_game_platform_v1(
            choice,
            _trimmed(values, "custom_platform"),
        )
    except ValueError as exc:
        field_key = "custom_platform" if choice == "custom" else "platform_choice"
        raise ProfileDrivenCreationFieldError(field_key, str(exc)) from exc


def _source_values(values: Mapping[str, str], title: str) -> tuple[str, str, str, str]:
    source_url = _trimmed(values, "source_url")
    explicit_kind = _trimmed(values, "source_kind")
    source_title = _trimmed(values, "source_title") or title
    source_channel = _trimmed(values, "source_channel_name")
    if source_url:
        try:
            parsed = urlsplit(source_url)
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError as exc:
            raise ProfileDrivenCreationFieldError(
                "source_url",
                "Source URL must be an absolute HTTP or HTTPS URL.",
            ) from exc
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.netloc
            or hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or any(character.isspace() for character in source_url)
        ):
            raise ProfileDrivenCreationFieldError(
                "source_url",
                "Source URL must be an absolute HTTP or HTTPS URL without credentials."
            )
        derived_kind = "youtube_video" if hostname.lower() in _YOUTUBE_HOSTS else "other_video"
    else:
        derived_kind = "manual_observation"
    source_kind = explicit_kind or derived_kind
    if source_kind not in {"youtube_video", "other_video", "manual_observation"}:
        raise ProfileDrivenCreationFieldError("source_kind", "Advanced source kind is unsupported.")
    if source_kind == "manual_observation" and source_url:
        raise ProfileDrivenCreationFieldError(
            "source_kind",
            "A manual observation must not have a source URL.",
        )
    if source_kind != "manual_observation" and not source_url:
        raise ProfileDrivenCreationFieldError(
            "source_url",
            "A media source requires one source URL.",
        )
    if source_kind == "manual_observation" and source_channel:
        raise ProfileDrivenCreationFieldError(
            "source_channel_name",
            "A manual observation must not have a source channel.",
        )
    return source_kind, source_url, source_title, source_channel


def _date_values(values: Mapping[str, str]) -> tuple[str | None, str]:
    played_date = _trimmed(values, "played_date") or None
    if played_date is not None:
        try:
            parsed_date = date.fromisoformat(played_date)
        except ValueError as exc:
            raise ProfileDrivenCreationFieldError(
                "played_date",
                "Date played must use exact YYYY-MM-DD.",
            ) from exc
        if parsed_date.isoformat() != played_date:
            raise ProfileDrivenCreationFieldError(
                "played_date",
                "Date played must use exact YYYY-MM-DD.",
            )
    played_at = _trimmed(values, "played_at")
    if played_at:
        try:
            parse_rfc3339_datetime(played_at, "played_at")
        except ValueError as exc:
            raise ProfileDrivenCreationFieldError("played_at", str(exc)) from exc
        if played_date is not None and played_at[:10] != played_date:
            raise ProfileDrivenCreationFieldError(
                "played_at",
                "Date played and exact date/time must use the same calendar date.",
            )
    return played_date, played_at


def prepare_profile_driven_match_creation_v1(
    values: Mapping[str, str],
    *,
    profile: LocalFrontendProfileV1 | None,
    expected_profile_generation: int,
    existing_match_ids: tuple[str, ...],
    entropy_source: Callable[[int], bytes],
) -> PreparedProfileDrivenMatchCreationV1:
    generation = _require_generation(expected_profile_generation)
    title = _trimmed(values, "match_title")
    played_date, played_at = _date_values(values)
    _validate_label(
        title,
        field_key="match_title",
        family="matches",
        played_date=played_date,
    )
    platform = _friendly_platform(values)
    selected = _select_players(values, profile)
    perspective_seat = _trimmed(values, "perspective_seat")
    if perspective_seat not in _SEATS:
        raise ProfileDrivenCreationFieldError(
            "perspective_seat",
            "Perspective must identify one visible Match Player.",
        )
    perspective_index = _SEATS.index(perspective_seat)
    source_kind, source_url, source_title, source_channel = _source_values(values, title)
    timecode_start = _trimmed(values, "match_timecode_start")
    timecode_end = _trimmed(values, "match_timecode_end")
    if source_kind == "manual_observation" and (timecode_start or timecode_end):
        raise ProfileDrivenCreationFieldError(
            "match_timecode_start" if timecode_start else "match_timecode_end",
            "Video timecodes require one media source.",
        )
    platform_ids = tuple(_trimmed(values, f"player_{index}_platform_id") for index in range(1, 4))
    save_players = _checkbox(values, "save_players")
    save_preferences = _checkbox(values, "save_preferences")
    if selected[perspective_index].known_player is None and save_preferences and not save_players:
        raise ProfileDrivenCreationFieldError(
            "save_preferences",
            "Saving a new preferred perspective also requires saving Players.",
        )

    base_values = {
        "match_id": "pending-match",
        "title": title,
        "game_platform": platform,
        "external_match_id": _trimmed(values, "external_match_id"),
        "played_at": played_at,
        "source_kind": source_kind,
        "source_url": source_url,
        "source_title": source_title,
        "source_channel_name": source_channel,
        "match_timecode_start": timecode_start,
        "match_timecode_end": timecode_end,
        **{f"player_{index}_id": f"pending-player-{index}" for index in range(1, 4)},
        **{
            f"player_{index}_label": player.display_name
            for index, player in enumerate(selected, start=1)
        },
        **{
            f"player_{index}_platform_id": platform_id
            for index, platform_id in enumerate(platform_ids, start=1)
        },
        "perspective_player_id": f"pending-player-{perspective_index + 1}",
    }
    new_players, player_ids, product_platform_ids = _materialize_players(
        selected,
        profile=profile,
        platform=platform,
        platform_ids=platform_ids,
        entropy_source=entropy_source,
    )
    match_id = generate_frontend_match_id_v1(
        existing_ids=existing_match_ids,
        entropy_source=entropy_source,
    )
    product_values = {
        **base_values,
        "match_id": match_id,
        **{f"player_{index}_id": player_id for index, player_id in enumerate(player_ids, start=1)},
        **{
            f"player_{index}_platform_id": platform_id or ""
            for index, platform_id in enumerate(product_platform_ids, start=1)
        },
        "perspective_player_id": player_ids[perspective_index],
    }
    profile_document = _profile_with_creation(
        profile,
        new_players=new_players,
        save_players=save_players,
        preferred_perspective_player_id=player_ids[perspective_index],
        save_perspective=save_preferences,
        preferred_game_platform=platform,
        save_platform=save_preferences,
        label=ManagedItemDisplayLabelV1(
            "matches",
            match_id,
            title,
            played_date,
        ),
    )
    return PreparedProfileDrivenMatchCreationV1(
        match_id=match_id,
        product_values=MappingProxyType(product_values),
        profile_document=profile_document,
        expected_profile_generation=generation,
    )


def prepare_profile_driven_learning_creation_v1(
    values: Mapping[str, str],
    *,
    profile: LocalFrontendProfileV1 | None,
    expected_profile_generation: int,
    existing_corpus_ids: tuple[str, ...],
    entropy_source: Callable[[int], bytes],
) -> PreparedProfileDrivenLearningCreationV1:
    generation = _require_generation(expected_profile_generation)
    collection_name = _trimmed(values, "collection_name")
    _validate_label(collection_name, field_key="collection_name", family="corpora")
    corpus_id = generate_frontend_corpus_id_v1(
        existing_ids=existing_corpus_ids,
        entropy_source=entropy_source,
    )
    profile_document = _profile_with_creation(
        profile,
        new_players=(),
        save_players=False,
        preferred_perspective_player_id=None,
        save_perspective=False,
        preferred_game_platform=None,
        save_platform=False,
        label=ManagedItemDisplayLabelV1("corpora", corpus_id, collection_name),
    )
    return PreparedProfileDrivenLearningCreationV1(
        corpus_id=corpus_id,
        profile_document=profile_document,
        expected_profile_generation=generation,
    )
