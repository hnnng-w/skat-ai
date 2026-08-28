from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)

if TYPE_CHECKING:
    from skatmind.learning_corpus_player_catalog import LearningCorpusPlayerCatalogV1

LEARNING_CORPUS_PLATFORM_ALIAS_VERSION = 1

LEARNING_CORPUS_PLATFORM_ALIAS_SOURCES: Final[tuple[str, ...]] = (
    "match_participant",
    "statistics_source",
)
LEARNING_CORPUS_PLATFORM_ALIAS_RESOLUTION_STATUSES: Final[tuple[str, ...]] = (
    "not_observed",
    "resolved",
    "conflict",
)

LEARNING_CORPUS_PLATFORM_ALIAS_HISTORY_POLICY = "retain_exact_observed_aliases_without_merge"
LEARNING_CORPUS_PLATFORM_ALIAS_CONFLICT_POLICY = "same_exact_alias_multiple_player_ids_reported"

_PLATFORM_ALIAS_OBSERVATION_ID_DOMAIN = b"skatmind\0learning_corpus_platform_alias_observation_v1\0"
_PLATFORM_ALIAS_CONFLICT_ID_DOMAIN = b"skatmind\0learning_corpus_platform_alias_conflict_v1\0"


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_identifier(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a non-empty, non-padded string{nullable}.")
    return value


def _require_hash(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value{nullable}.")
    return value


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlatformAliasObservationV1:
    """One exact platform identity observed for one stable Player."""

    learning_corpus_platform_alias_version: int = LEARNING_CORPUS_PLATFORM_ALIAS_VERSION
    platform_alias_observation_id: str
    alias_source: str
    player_id: str
    match_id: str
    match_snapshot_id: str
    player_match_observation_id: str
    statistics_observation_id: str | None
    platform_name: str
    platform_player_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlatformAliasObservationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        platform_alias_observation_id: str,
        alias_source: str,
        player_id: str,
        match_id: str,
        match_snapshot_id: str,
        player_match_observation_id: str,
        statistics_observation_id: str | None,
        platform_name: str,
        platform_player_id: str,
    ) -> LearningCorpusPlatformAliasObservationV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_platform_alias_version",
                LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            ),
            ("platform_alias_observation_id", platform_alias_observation_id),
            ("alias_source", alias_source),
            ("player_id", player_id),
            ("match_id", match_id),
            ("match_snapshot_id", match_snapshot_id),
            ("player_match_observation_id", player_match_observation_id),
            ("statistics_observation_id", statistics_observation_id),
            ("platform_name", platform_name),
            ("platform_player_id", platform_player_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_platform_alias_version,
            LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            "learning_corpus_platform_alias_version",
        )
        _require_hash(
            self.platform_alias_observation_id,
            "platform_alias_observation_id",
        )
        if self.alias_source not in LEARNING_CORPUS_PLATFORM_ALIAS_SOURCES:
            raise ValueError("alias_source must be one canonical platform alias source.")
        for field_name in (
            "player_id",
            "match_id",
            "platform_name",
            "platform_player_id",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        for field_name in (
            "match_snapshot_id",
            "player_match_observation_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        _require_hash(
            self.statistics_observation_id,
            "statistics_observation_id",
            allow_none=True,
        )
        if (self.alias_source == "match_participant") != (self.statistics_observation_id is None):
            raise ValueError(
                "statistics_observation_id is null exactly for match_participant aliases."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_platform_alias_version": (self.learning_corpus_platform_alias_version),
            "platform_alias_observation_id": self.platform_alias_observation_id,
            "alias_source": self.alias_source,
            "player_id": self.player_id,
            "match_id": self.match_id,
            "match_snapshot_id": self.match_snapshot_id,
            "player_match_observation_id": self.player_match_observation_id,
            "statistics_observation_id": self.statistics_observation_id,
            "platform_name": self.platform_name,
            "platform_player_id": self.platform_player_id,
        }


def _build_learning_corpus_platform_alias_observation_v1(
    *,
    alias_source: str,
    player_id: str,
    match_id: str,
    match_snapshot_id: str,
    player_match_observation_id: str,
    statistics_observation_id: str | None,
    platform_name: str,
    platform_player_id: str,
) -> LearningCorpusPlatformAliasObservationV1:
    material = {
        "learning_corpus_platform_alias_version": (LEARNING_CORPUS_PLATFORM_ALIAS_VERSION),
        "alias_source": alias_source,
        "player_id": player_id,
        "match_id": match_id,
        "match_snapshot_id": match_snapshot_id,
        "player_match_observation_id": player_match_observation_id,
        "statistics_observation_id": statistics_observation_id,
        "platform_name": platform_name,
        "platform_player_id": platform_player_id,
    }
    return LearningCorpusPlatformAliasObservationV1._from_validated(
        platform_alias_observation_id=_build_identifier(
            _PLATFORM_ALIAS_OBSERVATION_ID_DOMAIN,
            material,
        ),
        alias_source=alias_source,
        player_id=player_id,
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
        player_match_observation_id=player_match_observation_id,
        statistics_observation_id=statistics_observation_id,
        platform_name=platform_name,
        platform_player_id=platform_player_id,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlatformAliasConflictV1:
    """One exact platform alias observed for multiple stable Player IDs."""

    learning_corpus_platform_alias_version: int = LEARNING_CORPUS_PLATFORM_ALIAS_VERSION
    platform_alias_conflict_id: str
    platform_name: str
    platform_player_id: str
    player_ids: tuple[str, ...]
    platform_alias_observation_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlatformAliasConflictV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        platform_alias_conflict_id: str,
        platform_name: str,
        platform_player_id: str,
        player_ids: tuple[str, ...],
        platform_alias_observation_ids: tuple[str, ...],
    ) -> LearningCorpusPlatformAliasConflictV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_platform_alias_version",
                LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            ),
            ("platform_alias_conflict_id", platform_alias_conflict_id),
            ("platform_name", platform_name),
            ("platform_player_id", platform_player_id),
            ("player_ids", player_ids),
            (
                "platform_alias_observation_ids",
                platform_alias_observation_ids,
            ),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_platform_alias_version,
            LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            "learning_corpus_platform_alias_version",
        )
        _require_hash(self.platform_alias_conflict_id, "platform_alias_conflict_id")
        _require_identifier(self.platform_name, "platform_name")
        _require_identifier(self.platform_player_id, "platform_player_id")
        if (
            type(self.player_ids) is not tuple
            or len(self.player_ids) < 2
            or self.player_ids != tuple(sorted(set(self.player_ids)))
        ):
            raise ValueError("A conflict requires at least two unique sorted Player IDs.")
        for player_id in self.player_ids:
            _require_identifier(player_id, "player_ids")
        if type(
            self.platform_alias_observation_ids
        ) is not tuple or self.platform_alias_observation_ids != tuple(
            sorted(set(self.platform_alias_observation_ids))
        ):
            raise ValueError("Conflict observation IDs must be unique and sorted.")
        for observation_id in self.platform_alias_observation_ids:
            _require_hash(observation_id, "platform_alias_observation_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_platform_alias_version": (self.learning_corpus_platform_alias_version),
            "platform_alias_conflict_id": self.platform_alias_conflict_id,
            "platform_name": self.platform_name,
            "platform_player_id": self.platform_player_id,
            "player_ids": list(self.player_ids),
            "platform_alias_observation_ids": list(self.platform_alias_observation_ids),
        }


def _build_learning_corpus_platform_alias_conflict_v1(
    *,
    platform_name: str,
    platform_player_id: str,
    observations: tuple[LearningCorpusPlatformAliasObservationV1, ...],
) -> LearningCorpusPlatformAliasConflictV1:
    if not observations or any(
        type(item) is not LearningCorpusPlatformAliasObservationV1 for item in observations
    ):
        raise ValueError("observations must contain exact platform alias observations.")
    if any(
        item.platform_name != platform_name or item.platform_player_id != platform_player_id
        for item in observations
    ):
        raise ValueError("Conflict observations must use one exact platform alias.")
    player_ids = tuple(sorted({item.player_id for item in observations}))
    observation_ids = tuple(sorted({item.platform_alias_observation_id for item in observations}))
    material = {
        "learning_corpus_platform_alias_version": (LEARNING_CORPUS_PLATFORM_ALIAS_VERSION),
        "platform_name": platform_name,
        "platform_player_id": platform_player_id,
        "player_ids": list(player_ids),
        "platform_alias_observation_ids": list(observation_ids),
    }
    return LearningCorpusPlatformAliasConflictV1._from_validated(
        platform_alias_conflict_id=_build_identifier(
            _PLATFORM_ALIAS_CONFLICT_ID_DOMAIN,
            material,
        ),
        platform_name=platform_name,
        platform_player_id=platform_player_id,
        player_ids=player_ids,
        platform_alias_observation_ids=observation_ids,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlatformAliasResolutionV1:
    """One pure exact alias lookup result without identity mutation."""

    learning_corpus_platform_alias_version: int = LEARNING_CORPUS_PLATFORM_ALIAS_VERSION
    status: str
    platform_name: str
    platform_player_id: str
    player_id: str | None
    player_ids: tuple[str, ...]
    platform_alias_observation_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlatformAliasResolutionV1 must be constructed by its focused resolver."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        status: str,
        platform_name: str,
        platform_player_id: str,
        player_id: str | None,
        player_ids: tuple[str, ...],
        platform_alias_observation_ids: tuple[str, ...],
    ) -> LearningCorpusPlatformAliasResolutionV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_platform_alias_version",
                LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            ),
            ("status", status),
            ("platform_name", platform_name),
            ("platform_player_id", platform_player_id),
            ("player_id", player_id),
            ("player_ids", player_ids),
            (
                "platform_alias_observation_ids",
                platform_alias_observation_ids,
            ),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_platform_alias_version,
            LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
            "learning_corpus_platform_alias_version",
        )
        if self.status not in LEARNING_CORPUS_PLATFORM_ALIAS_RESOLUTION_STATUSES:
            raise ValueError("status must be one canonical alias resolution status.")
        _require_identifier(self.platform_name, "platform_name")
        _require_identifier(self.platform_player_id, "platform_player_id")
        _require_identifier(self.player_id, "player_id", allow_none=True)
        if type(self.player_ids) is not tuple or self.player_ids != tuple(
            sorted(set(self.player_ids))
        ):
            raise ValueError("player_ids must be unique and sorted.")
        for player_id in self.player_ids:
            _require_identifier(player_id, "player_ids")
        if type(
            self.platform_alias_observation_ids
        ) is not tuple or self.platform_alias_observation_ids != tuple(
            sorted(set(self.platform_alias_observation_ids))
        ):
            raise ValueError("platform_alias_observation_ids must be unique and sorted.")
        for observation_id in self.platform_alias_observation_ids:
            _require_hash(observation_id, "platform_alias_observation_ids")
        if self.status == "not_observed":
            if self.player_id is not None or self.player_ids or self.platform_alias_observation_ids:
                raise ValueError("A not-observed alias has no retained observations.")
        elif self.status == "resolved":
            if len(self.player_ids) != 1 or self.player_id != self.player_ids[0]:
                raise ValueError("A resolved alias identifies exactly one Player.")
        elif self.player_id is not None or len(self.player_ids) < 2:
            raise ValueError("A conflicting alias has at least two Players and no winner.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_platform_alias_version": (self.learning_corpus_platform_alias_version),
            "status": self.status,
            "platform_name": self.platform_name,
            "platform_player_id": self.platform_player_id,
            "player_id": self.player_id,
            "player_ids": list(self.player_ids),
            "platform_alias_observation_ids": list(self.platform_alias_observation_ids),
        }


def resolve_learning_corpus_platform_alias_v1(
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    platform_name: str,
    platform_player_id: str,
) -> LearningCorpusPlatformAliasResolutionV1:
    """Resolves one exact case-sensitive alias without mutation or merging."""
    from skatmind.learning_corpus_player_catalog import (
        LearningCorpusPlayerCatalogV1,
        _validate_learning_corpus_player_catalog_v1,
    )

    if type(player_catalog) is not LearningCorpusPlayerCatalogV1:
        raise ValueError("player_catalog must be an exact LearningCorpusPlayerCatalogV1.")
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    _require_identifier(platform_name, "platform_name")
    _require_identifier(platform_player_id, "platform_player_id")
    observations = tuple(
        alias
        for player in player_catalog.players
        for alias in player.platform_alias_observations
        if alias.platform_name == platform_name and alias.platform_player_id == platform_player_id
    )
    player_ids = tuple(sorted({item.player_id for item in observations}))
    observation_ids = tuple(sorted(item.platform_alias_observation_id for item in observations))
    if not observations:
        status = "not_observed"
        player_id = None
    elif len(player_ids) == 1:
        status = "resolved"
        player_id = player_ids[0]
    else:
        status = "conflict"
        player_id = None
    return LearningCorpusPlatformAliasResolutionV1._from_validated(
        status=status,
        platform_name=platform_name,
        platform_player_id=platform_player_id,
        player_id=player_id,
        player_ids=player_ids,
        platform_alias_observation_ids=observation_ids,
    )
