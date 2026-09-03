from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .frontend_identifier_generation import (
    build_known_player_handle_v1,
    generate_frontend_player_id_v1,
)
from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_contracts import (
    FrontendInterfacePreferencesV1,
    LocalFrontendProfileV1,
)
from .frontend_profile_operations import (
    InvalidFrontendProfileResetRequiredError,
    StaleFrontendProfileGenerationError,
    save_prepared_frontend_profile_v1,
)
from .profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
    normalize_player_display_name_v1,
)


@dataclass(frozen=True, slots=True)
class KnownPlayerMutationResultV1:
    status: str
    player: KnownPlayerV1

    def __post_init__(self) -> None:
        if self.status not in {"saved", "unchanged"}:
            raise ValueError("status must identify a successful profile write.")
        if type(self.player) is not KnownPlayerV1:
            raise ValueError("player must be an exact known Player.")


def _current_document(
    context,
    *,
    expected_generation: int,
) -> LocalFrontendProfileV1 | None:
    if type(expected_generation) is not int or expected_generation < 0:
        raise ValueError("expected_generation must be a non-negative integer.")
    with context.lock:
        state = context.frontend_profile
        if state.generation != expected_generation:
            raise StaleFrontendProfileGenerationError
        if state.load_status == "invalid":
            raise InvalidFrontendProfileResetRequiredError
        return state.document


def _build_updated(
    document: LocalFrontendProfileV1 | None,
    *,
    known_players: tuple[KnownPlayerV1, ...] | None = None,
    own_player_id: str | None = None,
    preserve_own_player: bool = True,
    preferred_perspective_player_id: str | None = None,
    preserve_preferred_perspective: bool = True,
    preferred_game_platform: str | None = None,
    preserve_preferred_platform: bool = True,
    interface_preferences: FrontendInterfacePreferencesV1 | None = None,
    managed_item_display_labels: tuple[ManagedItemDisplayLabelV1, ...] | None = None,
) -> LocalFrontendProfileV1:
    return build_local_frontend_profile_v1(
        revision=0 if document is None else document.revision + 1,
        language=None if document is None else document.language,
        interface_preferences=(
            FrontendInterfacePreferencesV1() if document is None else document.interface_preferences
        )
        if interface_preferences is None
        else interface_preferences,
        own_player_id=(None if document is None else document.own_player_id)
        if preserve_own_player
        else own_player_id,
        known_players=(() if document is None else document.known_players)
        if known_players is None
        else known_players,
        preferred_perspective_player_id=(
            None if document is None else document.preferred_perspective_player_id
        )
        if preserve_preferred_perspective
        else preferred_perspective_player_id,
        preferred_game_platform=(None if document is None else document.preferred_game_platform)
        if preserve_preferred_platform
        else preferred_game_platform,
        workflow_preferences=(
            build_local_frontend_profile_v1().workflow_preferences
            if document is None
            else document.workflow_preferences
        ),
        managed_item_display_labels=(
            () if document is None else document.managed_item_display_labels
        )
        if managed_item_display_labels is None
        else managed_item_display_labels,
    )


def resolve_known_player_handle_v1(
    document: LocalFrontendProfileV1 | None,
    handle: str,
) -> KnownPlayerV1:
    if type(handle) is not str or len(handle) != 64:
        raise ValueError("Unknown or stale known-Player selection.")
    if document is not None:
        for player in document.known_players:
            if build_known_player_handle_v1(player.player_id) == handle:
                return player
    raise ValueError("Unknown or stale known-Player selection.")


def add_known_player_v1(
    context,
    *,
    display_name: str,
    aliases: tuple[str, ...],
    platform_player_ids: tuple[KnownPlayerPlatformIdV1, ...],
    expected_generation: int,
    entropy_source: Callable[[int], bytes],
) -> KnownPlayerMutationResultV1:
    document = _current_document(context, expected_generation=expected_generation)
    existing = () if document is None else document.known_players
    normalized = normalize_player_display_name_v1(display_name)
    if any(
        normalize_player_display_name_v1(player.display_name) == normalized for player in existing
    ):
        raise ValueError("Duplicate display names must be explicitly disambiguated.")
    player = KnownPlayerV1(
        player_id=generate_frontend_player_id_v1(
            existing_ids=tuple(value.player_id for value in existing),
            entropy_source=entropy_source,
        ),
        display_name=display_name,
        aliases=aliases,
        platform_player_ids=platform_player_ids,
    )
    requested = _build_updated(document, known_players=(*existing, player))
    status = save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )
    return KnownPlayerMutationResultV1(status=status, player=player)


def replace_known_player_v1(
    context,
    *,
    player_handle: str,
    display_name: str,
    aliases: tuple[str, ...],
    platform_player_ids: tuple[KnownPlayerPlatformIdV1, ...],
    expected_generation: int,
) -> KnownPlayerMutationResultV1:
    document = _current_document(context, expected_generation=expected_generation)
    existing = resolve_known_player_handle_v1(document, player_handle)
    replacement = KnownPlayerV1(
        player_id=existing.player_id,
        display_name=display_name,
        aliases=aliases,
        platform_player_ids=platform_player_ids,
    )
    if replacement == existing:
        return KnownPlayerMutationResultV1(status="unchanged", player=existing)
    assert document is not None
    requested = _build_updated(
        document,
        known_players=tuple(
            replacement if player.player_id == existing.player_id else player
            for player in document.known_players
        ),
    )
    status = save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )
    return KnownPlayerMutationResultV1(status=status, player=replacement)


def remove_known_player_v1(
    context,
    *,
    player_handle: str,
    confirm_referenced: bool,
    expected_generation: int,
) -> str:
    if type(confirm_referenced) is not bool:
        raise ValueError("confirm_referenced must be a boolean.")
    document = _current_document(context, expected_generation=expected_generation)
    existing = resolve_known_player_handle_v1(document, player_handle)
    assert document is not None
    referenced = existing.player_id in {
        document.own_player_id,
        document.preferred_perspective_player_id,
    }
    if referenced and not confirm_referenced:
        raise ValueError("Removing this referenced Player requires explicit confirmation.")
    requested = _build_updated(
        document,
        known_players=tuple(
            player for player in document.known_players if player.player_id != existing.player_id
        ),
        own_player_id=(
            None if document.own_player_id == existing.player_id else document.own_player_id
        ),
        preserve_own_player=False,
        preferred_perspective_player_id=(
            None
            if document.preferred_perspective_player_id == existing.player_id
            else document.preferred_perspective_player_id
        ),
        preserve_preferred_perspective=False,
    )
    return save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )


def set_frontend_creation_preferences_v1(
    context,
    *,
    own_player_id: str | None,
    preferred_perspective_player_id: str | None,
    preferred_game_platform: str | None,
    advanced_settings_expanded: bool,
    expected_generation: int,
) -> str:
    document = _current_document(context, expected_generation=expected_generation)
    current_own_player_id = None if document is None else document.own_player_id
    current_perspective = None if document is None else document.preferred_perspective_player_id
    current_platform = None if document is None else document.preferred_game_platform
    current_advanced = (
        False if document is None else document.interface_preferences.advanced_settings_expanded
    )
    if (
        own_player_id == current_own_player_id
        and preferred_perspective_player_id == current_perspective
        and preferred_game_platform == current_platform
        and advanced_settings_expanded == current_advanced
    ):
        return "unchanged"
    requested = _build_updated(
        document,
        own_player_id=own_player_id,
        preserve_own_player=False,
        preferred_perspective_player_id=preferred_perspective_player_id,
        preserve_preferred_perspective=False,
        preferred_game_platform=preferred_game_platform,
        preserve_preferred_platform=False,
        interface_preferences=FrontendInterfacePreferencesV1(
            advanced_settings_expanded=advanced_settings_expanded
        ),
    )
    return save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )


def set_managed_item_display_label_v1(
    context,
    *,
    label: ManagedItemDisplayLabelV1,
    expected_generation: int,
) -> str:
    if type(label) is not ManagedItemDisplayLabelV1:
        raise ValueError("label must be an exact managed-item display label.")
    document = _current_document(context, expected_generation=expected_generation)
    current = () if document is None else document.managed_item_display_labels
    key = (label.family, label.product_id)
    existing = next(
        (value for value in current if (value.family, value.product_id) == key),
        None,
    )
    if existing == label:
        return "unchanged"
    retained = tuple(value for value in current if (value.family, value.product_id) != key)
    requested = _build_updated(
        document,
        managed_item_display_labels=(*retained, label),
    )
    return save_prepared_frontend_profile_v1(
        context,
        requested=requested,
        expected_generation=expected_generation,
    )
