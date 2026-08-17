from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from skat_ai.learning_corpus_identity import (
    LEARNING_CORPUS_PLAYER_IDENTITY_POLICY as _LEARNING_CORPUS_PLAYER_IDENTITY_POLICY,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    resume_learning_corpus_catalog_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_player_aliases import (
    LearningCorpusPlatformAliasConflictV1,
    LearningCorpusPlatformAliasObservationV1,
    _build_learning_corpus_platform_alias_conflict_v1,
    _build_learning_corpus_platform_alias_observation_v1,
)
from skat_ai.learning_corpus_player_statistics import (
    LearningCorpusPlayerStatisticsObservationV1,
    _build_learning_corpus_player_statistics_observation_v1,
)
from skat_ai.learning_corpus_references import LearningCorpusPlayerObservationV1
from skat_ai.rfc3339 import parse_rfc3339_datetime

LEARNING_CORPUS_PLAYER_CATALOG_VERSION = 1
LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION = 1
LEARNING_CORPUS_PLAYER_IDENTITY_POLICY = _LEARNING_CORPUS_PLAYER_IDENTITY_POLICY

LEARNING_CORPUS_PLAYER_CATALOG_SOURCE_POLICY = "explicit_current_match_snapshots_only"
LEARNING_CORPUS_PLAYER_LABEL_HISTORY_POLICY = "retain_observed_labels_without_canonicalization"
LEARNING_CORPUS_PLAYER_CATALOG_DERIVATION_POLICY = "rebuild_from_strict_store_without_persistence"
LEARNING_CORPUS_PLAYER_CATALOG_PRIVACY_POLICY = "private_local_unredacted_player_history"

_PLAYER_CATALOG_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_player_catalog_v1\0"
_PLAYER_MATCH_OBSERVATION_ID_DOMAIN = b"skat-ai\0learning_corpus_player_match_observation_v1\0"


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


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerMatchObservationV1:
    """One Player's exact descriptive observation in one current Match Snapshot."""

    learning_corpus_player_match_observation_version: int = (
        LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION
    )
    player_match_observation_id: str
    player_id: str
    match_id: str
    match_snapshot_id: str
    player_observation_id: str
    workspace_revision: int
    table_place: str
    player_label: str | None
    game_platform: str
    platform_player_id: str | None
    match_title: str
    external_match_id: str | None
    played_at: str | None
    source_kind: str
    source_title: str
    perspective_player: bool
    statistics_snapshot_id: str | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlayerMatchObservationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        player_match_observation_id: str,
        player_id: str,
        match_id: str,
        match_snapshot_id: str,
        player_observation_id: str,
        workspace_revision: int,
        table_place: str,
        player_label: str | None,
        game_platform: str,
        platform_player_id: str | None,
        match_title: str,
        external_match_id: str | None,
        played_at: str | None,
        source_kind: str,
        source_title: str,
        perspective_player: bool,
        statistics_snapshot_id: str | None,
    ) -> LearningCorpusPlayerMatchObservationV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_player_match_observation_version",
                LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION,
            ),
            ("player_match_observation_id", player_match_observation_id),
            ("player_id", player_id),
            ("match_id", match_id),
            ("match_snapshot_id", match_snapshot_id),
            ("player_observation_id", player_observation_id),
            ("workspace_revision", workspace_revision),
            ("table_place", table_place),
            ("player_label", player_label),
            ("game_platform", game_platform),
            ("platform_player_id", platform_player_id),
            ("match_title", match_title),
            ("external_match_id", external_match_id),
            ("played_at", played_at),
            ("source_kind", source_kind),
            ("source_title", source_title),
            ("perspective_player", perspective_player),
            ("statistics_snapshot_id", statistics_snapshot_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_player_match_observation_version,
            LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION,
            "learning_corpus_player_match_observation_version",
        )
        for field_name in (
            "player_match_observation_id",
            "match_snapshot_id",
            "player_observation_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in (
            "player_id",
            "match_id",
            "table_place",
            "game_platform",
            "match_title",
            "source_kind",
            "source_title",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        for field_name in (
            "player_label",
            "platform_player_id",
            "external_match_id",
            "played_at",
            "statistics_snapshot_id",
        ):
            _require_identifier(getattr(self, field_name), field_name, allow_none=True)
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if self.played_at is not None:
            parse_rfc3339_datetime(self.played_at, "played_at")
        _require_boolean(self.perspective_player, "perspective_player")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_player_match_observation_version": (
                self.learning_corpus_player_match_observation_version
            ),
            "player_match_observation_id": self.player_match_observation_id,
            "player_id": self.player_id,
            "match_id": self.match_id,
            "match_snapshot_id": self.match_snapshot_id,
            "player_observation_id": self.player_observation_id,
            "workspace_revision": self.workspace_revision,
            "table_place": self.table_place,
            "player_label": self.player_label,
            "game_platform": self.game_platform,
            "platform_player_id": self.platform_player_id,
            "match_title": self.match_title,
            "external_match_id": self.external_match_id,
            "played_at": self.played_at,
            "source_kind": self.source_kind,
            "source_title": self.source_title,
            "perspective_player": self.perspective_player,
            "statistics_snapshot_id": self.statistics_snapshot_id,
        }


def _build_player_match_observation_v1(
    *,
    snapshot_id: str,
    workspace_revision: int,
    source_observation: LearningCorpusPlayerObservationV1,
    match_id: str,
    match_title: str,
    external_match_id: str | None,
    played_at: str | None,
    source_kind: str,
    source_title: str,
    perspective_player_id: str,
) -> LearningCorpusPlayerMatchObservationV1:
    if type(source_observation) is not LearningCorpusPlayerObservationV1:
        raise ValueError("source_observation must be an exact Player Observation.")
    if source_observation.match_snapshot_id != snapshot_id:
        raise ValueError("Player Observation must belong to the current Snapshot.")
    material = {
        "learning_corpus_player_match_observation_version": (
            LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION
        ),
        "match_snapshot_id": snapshot_id,
        "player_observation_id": source_observation.player_observation_id,
        "player_id": source_observation.player_id,
    }
    return LearningCorpusPlayerMatchObservationV1._from_validated(
        player_match_observation_id=_build_identifier(
            _PLAYER_MATCH_OBSERVATION_ID_DOMAIN,
            material,
        ),
        player_id=source_observation.player_id,
        match_id=match_id,
        match_snapshot_id=snapshot_id,
        player_observation_id=source_observation.player_observation_id,
        workspace_revision=workspace_revision,
        table_place=source_observation.table_place,
        player_label=source_observation.player_label,
        game_platform=source_observation.game_platform,
        platform_player_id=source_observation.platform_player_id,
        match_title=match_title,
        external_match_id=external_match_id,
        played_at=played_at,
        source_kind=source_kind,
        source_title=source_title,
        perspective_player=source_observation.player_id == perspective_player_id,
        statistics_snapshot_id=source_observation.statistics_snapshot_id,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerCatalogEntryV1:
    """One exact stable Player's current-Match observations and Statistics history."""

    learning_corpus_player_catalog_version: int = LEARNING_CORPUS_PLAYER_CATALOG_VERSION
    player_id: str
    match_observations: tuple[LearningCorpusPlayerMatchObservationV1, ...]
    platform_alias_observations: tuple[LearningCorpusPlatformAliasObservationV1, ...]
    statistics_observations: tuple[LearningCorpusPlayerStatisticsObservationV1, ...]
    observed_labels: tuple[str, ...]
    match_ids: tuple[str, ...]
    current_match_snapshot_ids: tuple[str, ...]
    match_count: int
    statistics_observation_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlayerCatalogEntryV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        player_id: str,
        match_observations: tuple[LearningCorpusPlayerMatchObservationV1, ...],
        platform_alias_observations: tuple[LearningCorpusPlatformAliasObservationV1, ...],
        statistics_observations: tuple[LearningCorpusPlayerStatisticsObservationV1, ...],
        observed_labels: tuple[str, ...],
        match_ids: tuple[str, ...],
        current_match_snapshot_ids: tuple[str, ...],
        match_count: int,
        statistics_observation_count: int,
    ) -> LearningCorpusPlayerCatalogEntryV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_player_catalog_version",
                LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
            ),
            ("player_id", player_id),
            ("match_observations", match_observations),
            ("platform_alias_observations", platform_alias_observations),
            ("statistics_observations", statistics_observations),
            ("observed_labels", observed_labels),
            ("match_ids", match_ids),
            ("current_match_snapshot_ids", current_match_snapshot_ids),
            ("match_count", match_count),
            ("statistics_observation_count", statistics_observation_count),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_player_catalog_version,
            LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
            "learning_corpus_player_catalog_version",
        )
        _require_identifier(self.player_id, "player_id")
        if type(self.match_observations) is not tuple or not self.match_observations:
            raise ValueError("A Player Catalog entry requires Match observations.")
        for observation in self.match_observations:
            if type(observation) is not LearningCorpusPlayerMatchObservationV1:
                raise ValueError("match_observations must contain exact observations.")
            observation._validate()
            if observation.player_id != self.player_id:
                raise ValueError("Match observations must use the entry Player ID.")
        if self.match_observations != tuple(
            sorted(
                self.match_observations,
                key=lambda item: (item.match_id, item.match_snapshot_id),
            )
        ):
            raise ValueError("Match observations must use canonical Match order.")
        if type(self.platform_alias_observations) is not tuple:
            raise ValueError("platform_alias_observations must be immutable.")
        for observation in self.platform_alias_observations:
            if type(observation) is not LearningCorpusPlatformAliasObservationV1:
                raise ValueError("Platform aliases must contain exact observations.")
            observation._validate()
            if observation.player_id != self.player_id:
                raise ValueError("Platform aliases must use the entry Player ID.")
        if self.platform_alias_observations != tuple(
            sorted(
                self.platform_alias_observations,
                key=lambda item: (
                    item.platform_name,
                    item.platform_player_id,
                    item.alias_source,
                    item.match_id,
                    item.platform_alias_observation_id,
                ),
            )
        ):
            raise ValueError("Platform aliases must use canonical exact-alias order.")
        if type(self.statistics_observations) is not tuple:
            raise ValueError("statistics_observations must be immutable.")
        for observation in self.statistics_observations:
            if type(observation) is not LearningCorpusPlayerStatisticsObservationV1:
                raise ValueError("Statistics history must contain exact observations.")
            observation._validate()
            if observation.player_id != self.player_id:
                raise ValueError("Statistics history must use the entry Player ID.")
        if self.statistics_observations != tuple(
            sorted(
                self.statistics_observations,
                key=lambda item: (
                    parse_rfc3339_datetime(item.captured_at, "captured_at"),
                    item.statistics_observation_id,
                ),
            )
        ):
            raise ValueError("Statistics observations must use chronological order.")
        if type(self.observed_labels) is not tuple or self.observed_labels != tuple(
            sorted(set(self.observed_labels))
        ):
            raise ValueError("observed_labels must be unique and sorted.")
        for label in self.observed_labels:
            _require_identifier(label, "observed_labels")
        expected_match_ids = tuple(item.match_id for item in self.match_observations)
        expected_snapshot_ids = tuple(item.match_snapshot_id for item in self.match_observations)
        if self.match_ids != expected_match_ids:
            raise ValueError("match_ids must reconcile with Match observations.")
        if self.current_match_snapshot_ids != expected_snapshot_ids:
            raise ValueError("current_match_snapshot_ids must reconcile with Match observations.")
        if len(set(self.match_ids)) != len(self.match_ids):
            raise ValueError("A Player can occur only once in each current Match.")
        _require_non_negative_integer(self.match_count, "match_count")
        _require_non_negative_integer(
            self.statistics_observation_count,
            "statistics_observation_count",
        )
        if self.match_count != len(self.match_observations):
            raise ValueError("match_count must reconcile exactly.")
        if self.statistics_observation_count != len(self.statistics_observations):
            raise ValueError("statistics_observation_count must reconcile exactly.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_player_catalog_version": (self.learning_corpus_player_catalog_version),
            "player_id": self.player_id,
            "match_observations": [item.to_dict() for item in self.match_observations],
            "platform_alias_observations": [
                item.to_dict() for item in self.platform_alias_observations
            ],
            "statistics_observations": [item.to_dict() for item in self.statistics_observations],
            "observed_labels": list(self.observed_labels),
            "match_ids": list(self.match_ids),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "match_count": self.match_count,
            "statistics_observation_count": self.statistics_observation_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerCatalogV1:
    """One deterministic non-persisted Player view over explicit current Matches."""

    learning_corpus_player_catalog_version: int = LEARNING_CORPUS_PLAYER_CATALOG_VERSION
    player_catalog_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    player_count: int
    match_observation_count: int
    statistics_observation_count: int
    players: tuple[LearningCorpusPlayerCatalogEntryV1, ...]
    platform_alias_conflicts: tuple[LearningCorpusPlatformAliasConflictV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusPlayerCatalogV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        player_catalog_fingerprint: str,
        corpus_id: str,
        source_catalog_revision: int,
        source_catalog_fingerprint: str,
        source_catalog_content_fingerprint: str,
        current_match_snapshot_ids: tuple[str, ...],
        retained_match_snapshot_count: int,
        current_match_count: int,
        orphan_match_snapshot_count: int,
        player_count: int,
        match_observation_count: int,
        statistics_observation_count: int,
        players: tuple[LearningCorpusPlayerCatalogEntryV1, ...],
        platform_alias_conflicts: tuple[LearningCorpusPlatformAliasConflictV1, ...],
    ) -> LearningCorpusPlayerCatalogV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_player_catalog_version",
                LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
            ),
            ("player_catalog_fingerprint", player_catalog_fingerprint),
            ("corpus_id", corpus_id),
            ("source_catalog_revision", source_catalog_revision),
            ("source_catalog_fingerprint", source_catalog_fingerprint),
            (
                "source_catalog_content_fingerprint",
                source_catalog_content_fingerprint,
            ),
            ("current_match_snapshot_ids", current_match_snapshot_ids),
            ("retained_match_snapshot_count", retained_match_snapshot_count),
            ("current_match_count", current_match_count),
            ("orphan_match_snapshot_count", orphan_match_snapshot_count),
            ("player_count", player_count),
            ("match_observation_count", match_observation_count),
            ("statistics_observation_count", statistics_observation_count),
            ("players", players),
            ("platform_alias_conflicts", platform_alias_conflicts),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_corpus_player_catalog_version,
            LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
            "learning_corpus_player_catalog_version",
        )
        _require_hash(self.player_catalog_fingerprint, "player_catalog_fingerprint")
        _require_identifier(self.corpus_id, "corpus_id")
        _require_non_negative_integer(
            self.source_catalog_revision,
            "source_catalog_revision",
        )
        _require_hash(self.source_catalog_fingerprint, "source_catalog_fingerprint")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        if type(self.current_match_snapshot_ids) is not tuple:
            raise ValueError("current_match_snapshot_ids must be immutable.")
        for snapshot_id in self.current_match_snapshot_ids:
            _require_hash(snapshot_id, "current_match_snapshot_ids")
        if len(self.current_match_snapshot_ids) != len(set(self.current_match_snapshot_ids)):
            raise ValueError("Current Match Snapshot IDs must be unique.")
        for field_name in (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "player_count",
            "match_observation_count",
            "statistics_observation_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.retained_match_snapshot_count < self.current_match_count:
            raise ValueError("Retained Snapshot count cannot be below Current count.")
        if type(self.players) is not tuple:
            raise ValueError("players must be immutable.")
        for player in self.players:
            if type(player) is not LearningCorpusPlayerCatalogEntryV1:
                raise ValueError("players must contain exact Player Catalog entries.")
            player._validate()
        if self.players != tuple(sorted(self.players, key=lambda item: item.player_id)):
            raise ValueError("Players must use exact stable Player-ID order.")
        if len({item.player_id for item in self.players}) != len(self.players):
            raise ValueError("Player Catalog entries must have unique stable IDs.")
        if self.player_count != len(self.players):
            raise ValueError("player_count must reconcile exactly.")
        expected_match_count = sum(item.match_count for item in self.players)
        expected_statistics_count = sum(item.statistics_observation_count for item in self.players)
        if self.match_observation_count != expected_match_count:
            raise ValueError("match_observation_count must reconcile exactly.")
        if self.statistics_observation_count != expected_statistics_count:
            raise ValueError("statistics_observation_count must reconcile exactly.")
        if self.match_observation_count != self.current_match_count * 3:
            raise ValueError("Each Current Match must contribute exactly three Players.")
        observed_current_ids = {
            observation.match_snapshot_id
            for player in self.players
            for observation in player.match_observations
        }
        if observed_current_ids != set(self.current_match_snapshot_ids):
            raise ValueError("Player entries must cover exactly the Current Snapshots.")
        if type(self.platform_alias_conflicts) is not tuple:
            raise ValueError("platform_alias_conflicts must be immutable.")
        for conflict in self.platform_alias_conflicts:
            if type(conflict) is not LearningCorpusPlatformAliasConflictV1:
                raise ValueError("Alias conflicts must contain exact conflict values.")
            conflict._validate()
        if self.platform_alias_conflicts != tuple(
            sorted(
                self.platform_alias_conflicts,
                key=lambda item: (item.platform_name, item.platform_player_id),
            )
        ):
            raise ValueError("Alias conflicts must use exact alias order.")
        if verify_fingerprint:
            expected = _build_identifier(
                _PLAYER_CATALOG_FINGERPRINT_DOMAIN,
                _player_catalog_fingerprint_material_v1(self),
            )
            if self.player_catalog_fingerprint != expected:
                raise ValueError("player_catalog_fingerprint must cover the exact Catalog.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_player_catalog_version": (self.learning_corpus_player_catalog_version),
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "player_count": self.player_count,
            "match_observation_count": self.match_observation_count,
            "statistics_observation_count": self.statistics_observation_count,
            "players": [item.to_dict() for item in self.players],
            "platform_alias_conflicts": [item.to_dict() for item in self.platform_alias_conflicts],
        }


def _player_catalog_fingerprint_material_v1(
    catalog: LearningCorpusPlayerCatalogV1,
) -> dict[str, Any]:
    material = catalog.to_dict()
    del material["player_catalog_fingerprint"]
    return material


def _validate_learning_corpus_player_catalog_v1(
    catalog: LearningCorpusPlayerCatalogV1,
) -> None:
    if type(catalog) is not LearningCorpusPlayerCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusPlayerCatalogV1.")
    catalog._validate(verify_fingerprint=True)


def _build_player_entry_v1(
    *,
    player_id: str,
    match_observations: list[LearningCorpusPlayerMatchObservationV1],
    alias_observations: list[LearningCorpusPlatformAliasObservationV1],
    statistics_observations: list[LearningCorpusPlayerStatisticsObservationV1],
) -> LearningCorpusPlayerCatalogEntryV1:
    ordered_matches = tuple(
        sorted(
            match_observations,
            key=lambda item: (item.match_id, item.match_snapshot_id),
        )
    )
    ordered_aliases = tuple(
        sorted(
            alias_observations,
            key=lambda item: (
                item.platform_name,
                item.platform_player_id,
                item.alias_source,
                item.match_id,
                item.platform_alias_observation_id,
            ),
        )
    )
    ordered_statistics = tuple(
        sorted(
            statistics_observations,
            key=lambda item: (
                parse_rfc3339_datetime(item.captured_at, "captured_at"),
                item.statistics_observation_id,
            ),
        )
    )
    labels = {
        observation.player_label
        for observation in ordered_matches
        if observation.player_label is not None
    }
    labels.update(
        observation.statistics_record.player_label
        for observation in ordered_statistics
        if observation.statistics_record.player_label is not None
    )
    return LearningCorpusPlayerCatalogEntryV1._from_validated(
        player_id=player_id,
        match_observations=ordered_matches,
        platform_alias_observations=ordered_aliases,
        statistics_observations=ordered_statistics,
        observed_labels=tuple(sorted(labels)),
        match_ids=tuple(item.match_id for item in ordered_matches),
        current_match_snapshot_ids=tuple(item.match_snapshot_id for item in ordered_matches),
        match_count=len(ordered_matches),
        statistics_observation_count=len(ordered_statistics),
    )


def build_learning_corpus_player_catalog_v1(
    store: LearningCorpusStoreResumeResultV1,
) -> LearningCorpusPlayerCatalogV1:
    """Derives one deterministic current-Snapshot Player Catalog without I/O."""
    if type(store) is not LearningCorpusStoreResumeResultV1:
        raise ValueError("store must be an exact LearningCorpusStoreResumeResultV1.")
    resumed_document = resume_learning_corpus_catalog_document_v1(store.document.to_dict())
    if resumed_document != store.document:
        raise ValueError("Store Catalog document must equal its strict reconstruction.")
    store._validate_structure(validate_snapshots=True)
    source_document = store.document
    source_catalog = source_document.catalog
    snapshots_by_id = {snapshot.match_snapshot_id: snapshot for snapshot in store.match_snapshots}
    current_snapshots = tuple(
        snapshots_by_id[selection.match_snapshot_id] for selection in source_catalog.current_matches
    )

    grouped_matches: dict[str, list[LearningCorpusPlayerMatchObservationV1]] = {}
    grouped_aliases: dict[str, list[LearningCorpusPlatformAliasObservationV1]] = {}
    grouped_statistics: dict[
        str,
        list[LearningCorpusPlayerStatisticsObservationV1],
    ] = {}
    all_aliases: list[LearningCorpusPlatformAliasObservationV1] = []

    for snapshot in current_snapshots:
        definition = snapshot.workspace.match_definition
        if snapshot.match_id != definition.match_id:
            raise ValueError("Current Snapshot Match identity must reconcile.")
        for participant, source_observation in zip(
            definition.participants,
            snapshot.player_observations,
            strict=True,
        ):
            if (
                source_observation.player_id != participant.player_id
                or source_observation.table_place != participant.table_place
            ):
                raise ValueError("Player Observation must reconcile with its participant.")
            match_observation = _build_player_match_observation_v1(
                snapshot_id=snapshot.match_snapshot_id,
                workspace_revision=snapshot.workspace_revision,
                source_observation=source_observation,
                match_id=definition.match_id,
                match_title=definition.title,
                external_match_id=definition.external_match_id,
                played_at=definition.played_at,
                source_kind=definition.source.source_kind,
                source_title=definition.source.source_title,
                perspective_player_id=definition.perspective_player_id,
            )
            player_id = participant.player_id
            grouped_matches.setdefault(player_id, []).append(match_observation)
            aliases = grouped_aliases.setdefault(player_id, [])
            statistics = grouped_statistics.setdefault(player_id, [])

            if participant.platform_player_id is not None:
                alias = _build_learning_corpus_platform_alias_observation_v1(
                    alias_source="match_participant",
                    player_id=player_id,
                    match_id=definition.match_id,
                    match_snapshot_id=snapshot.match_snapshot_id,
                    player_match_observation_id=(match_observation.player_match_observation_id),
                    statistics_observation_id=None,
                    platform_name=definition.game_platform,
                    platform_player_id=participant.platform_player_id,
                )
                aliases.append(alias)
                all_aliases.append(alias)

            statistics_snapshot = participant.statistics_snapshot
            if statistics_snapshot is None:
                if source_observation.statistics_snapshot_id is not None:
                    raise ValueError("Player Observation Statistics identity must reconcile.")
                continue
            if source_observation.statistics_snapshot_id != statistics_snapshot.snapshot_id:
                raise ValueError("Player Observation Statistics identity must reconcile.")
            statistics_observation = _build_learning_corpus_player_statistics_observation_v1(
                player_id=player_id,
                match_id=definition.match_id,
                match_snapshot_id=snapshot.match_snapshot_id,
                player_match_observation_id=(match_observation.player_match_observation_id),
                player_observation_id=source_observation.player_observation_id,
                statistics_snapshot=statistics_snapshot,
                source_match_played_at=definition.played_at,
            )
            statistics.append(statistics_observation)
            source = statistics_observation.statistics_record.source
            if source.source_type == "online_platform" and source.source_player_id is not None:
                alias = _build_learning_corpus_platform_alias_observation_v1(
                    alias_source="statistics_source",
                    player_id=player_id,
                    match_id=definition.match_id,
                    match_snapshot_id=snapshot.match_snapshot_id,
                    player_match_observation_id=(match_observation.player_match_observation_id),
                    statistics_observation_id=(statistics_observation.statistics_observation_id),
                    platform_name=source.source_name,
                    platform_player_id=source.source_player_id,
                )
                aliases.append(alias)
                all_aliases.append(alias)

    players = tuple(
        _build_player_entry_v1(
            player_id=player_id,
            match_observations=grouped_matches[player_id],
            alias_observations=grouped_aliases[player_id],
            statistics_observations=grouped_statistics[player_id],
        )
        for player_id in sorted(grouped_matches)
    )
    aliases_by_key: dict[
        tuple[str, str],
        list[LearningCorpusPlatformAliasObservationV1],
    ] = {}
    for alias in all_aliases:
        aliases_by_key.setdefault(
            (alias.platform_name, alias.platform_player_id),
            [],
        ).append(alias)
    conflicts = tuple(
        _build_learning_corpus_platform_alias_conflict_v1(
            platform_name=platform_name,
            platform_player_id=platform_player_id,
            observations=tuple(aliases_by_key[(platform_name, platform_player_id)]),
        )
        for platform_name, platform_player_id in sorted(aliases_by_key)
        if len({item.player_id for item in aliases_by_key[(platform_name, platform_player_id)]}) > 1
    )
    current_snapshot_ids = tuple(
        selection.match_snapshot_id for selection in source_catalog.current_matches
    )
    catalog_values = {
        "corpus_id": source_catalog.corpus_id,
        "source_catalog_revision": source_catalog.revision,
        "source_catalog_fingerprint": source_document.catalog_fingerprint,
        "source_catalog_content_fingerprint": source_document.content_fingerprint,
        "current_match_snapshot_ids": current_snapshot_ids,
        "retained_match_snapshot_count": len(store.match_snapshots),
        "current_match_count": len(current_snapshots),
        "orphan_match_snapshot_count": len(store.orphan_match_snapshot_ids),
        "player_count": len(players),
        "match_observation_count": sum(item.match_count for item in players),
        "statistics_observation_count": sum(item.statistics_observation_count for item in players),
        "players": players,
        "platform_alias_conflicts": conflicts,
    }
    fingerprint_material = {
        "learning_corpus_player_catalog_version": (LEARNING_CORPUS_PLAYER_CATALOG_VERSION),
        **{
            key: (
                [item.to_dict() for item in value]
                if key in {"players", "platform_alias_conflicts"}
                else list(value)
                if key == "current_match_snapshot_ids"
                else value
            )
            for key, value in catalog_values.items()
        },
    }
    return LearningCorpusPlayerCatalogV1._from_validated(
        player_catalog_fingerprint=_build_identifier(
            _PLAYER_CATALOG_FINGERPRINT_DOMAIN,
            fingerprint_material,
        ),
        **catalog_values,
    )
