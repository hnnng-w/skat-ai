from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.learning_corpus_identity import LEARNING_CORPUS_OBJECT_KINDS
from skat_ai.learning_corpus_match_snapshot import (
    LearningCorpusMatchSnapshotV1,
    validate_learning_corpus_match_snapshot_v1,
)

LEARNING_CORPUS_CATALOG_VERSION = 1
LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION = 1

LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS = (
    "new_match",
    "duplicate_snapshot",
    "newer_revision",
    "older_revision",
    "same_revision_content_conflict",
)

_MATCH_SNAPSHOT_OBJECT_KIND = LEARNING_CORPUS_OBJECT_KINDS[0]


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_identifier(value, field_name)


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


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusMatchSnapshotCatalogEntryV1:
    """One lightweight summary of a validated Match Snapshot."""

    learning_corpus_catalog_version: int = LEARNING_CORPUS_CATALOG_VERSION
    object_kind: str
    match_snapshot_id: str
    match_id: str
    workspace_revision: int
    source_workspace_fingerprint: str
    source_content_fingerprint: str
    played_at: str | None
    source_kind: str
    source_title: str
    game_platform: str
    perspective_player_id: str
    player_ids: tuple[str, ...]
    observed_game_count: int
    passed_deal_count: int
    empty_slot_count: int
    decision_count: int
    commentary_count: int
    response_link_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusMatchSnapshotCatalogEntryV1 must be constructed by its "
            "focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        match_snapshot_id: str,
        match_id: str,
        workspace_revision: int,
        source_workspace_fingerprint: str,
        source_content_fingerprint: str,
        played_at: str | None,
        source_kind: str,
        source_title: str,
        game_platform: str,
        perspective_player_id: str,
        player_ids: tuple[str, ...],
        observed_game_count: int,
        passed_deal_count: int,
        empty_slot_count: int,
        decision_count: int,
        commentary_count: int,
        response_link_count: int,
    ) -> LearningCorpusMatchSnapshotCatalogEntryV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_catalog_version", LEARNING_CORPUS_CATALOG_VERSION),
            ("object_kind", _MATCH_SNAPSHOT_OBJECT_KIND),
            ("match_snapshot_id", match_snapshot_id),
            ("match_id", match_id),
            ("workspace_revision", workspace_revision),
            ("source_workspace_fingerprint", source_workspace_fingerprint),
            ("source_content_fingerprint", source_content_fingerprint),
            ("played_at", played_at),
            ("source_kind", source_kind),
            ("source_title", source_title),
            ("game_platform", game_platform),
            ("perspective_player_id", perspective_player_id),
            ("player_ids", player_ids),
            ("observed_game_count", observed_game_count),
            ("passed_deal_count", passed_deal_count),
            ("empty_slot_count", empty_slot_count),
            ("decision_count", decision_count),
            ("commentary_count", commentary_count),
            ("response_link_count", response_link_count),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_catalog_version,
            LEARNING_CORPUS_CATALOG_VERSION,
            "learning_corpus_catalog_version",
        )
        if self.object_kind != _MATCH_SNAPSHOT_OBJECT_KIND:
            raise ValueError("Catalog entry object_kind must be match_workspace_snapshot.")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_identifier(self.match_id, "match_id")
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        _require_hash(self.source_workspace_fingerprint, "source_workspace_fingerprint")
        _require_hash(self.source_content_fingerprint, "source_content_fingerprint")
        _require_optional_identifier(self.played_at, "played_at")
        _require_identifier(self.source_kind, "source_kind")
        _require_identifier(self.source_title, "source_title")
        _require_identifier(self.game_platform, "game_platform")
        _require_identifier(self.perspective_player_id, "perspective_player_id")
        if type(self.player_ids) is not tuple or len(self.player_ids) != 3:
            raise ValueError("player_ids must contain exactly three canonical Players.")
        for player_id in self.player_ids:
            _require_identifier(player_id, "player_ids")
        if len(set(self.player_ids)) != 3:
            raise ValueError("player_ids must contain three unique Players.")
        for field_name in (
            "observed_game_count",
            "passed_deal_count",
            "empty_slot_count",
            "decision_count",
            "commentary_count",
            "response_link_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.observed_game_count + self.passed_deal_count + self.empty_slot_count != 36:
            raise ValueError("Catalog entry Slot counts must reconcile to 36.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_catalog_version": self.learning_corpus_catalog_version,
            "object_kind": self.object_kind,
            "match_snapshot_id": self.match_snapshot_id,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "source_workspace_fingerprint": self.source_workspace_fingerprint,
            "source_content_fingerprint": self.source_content_fingerprint,
            "played_at": self.played_at,
            "source_kind": self.source_kind,
            "source_title": self.source_title,
            "game_platform": self.game_platform,
            "perspective_player_id": self.perspective_player_id,
            "player_ids": list(self.player_ids),
            "observed_game_count": self.observed_game_count,
            "passed_deal_count": self.passed_deal_count,
            "empty_slot_count": self.empty_slot_count,
            "decision_count": self.decision_count,
            "commentary_count": self.commentary_count,
            "response_link_count": self.response_link_count,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusCurrentMatchSelectionV1:
    """One explicit current Snapshot selection for one logical Match."""

    learning_corpus_catalog_version: int = LEARNING_CORPUS_CATALOG_VERSION
    match_id: str
    match_snapshot_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusCurrentMatchSelectionV1 must be constructed by its "
            "focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        match_id: str,
        match_snapshot_id: str,
    ) -> LearningCorpusCurrentMatchSelectionV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_catalog_version",
            LEARNING_CORPUS_CATALOG_VERSION,
        )
        object.__setattr__(value, "match_id", match_id)
        object.__setattr__(value, "match_snapshot_id", match_snapshot_id)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_catalog_version,
            LEARNING_CORPUS_CATALOG_VERSION,
            "learning_corpus_catalog_version",
        )
        _require_identifier(self.match_id, "match_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_catalog_version": self.learning_corpus_catalog_version,
            "match_id": self.match_id,
            "match_snapshot_id": self.match_snapshot_id,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusCatalogV1:
    """One immutable lightweight manifest with explicit current selections."""

    learning_corpus_catalog_version: int = LEARNING_CORPUS_CATALOG_VERSION
    corpus_id: str
    revision: int
    match_snapshots: tuple[LearningCorpusMatchSnapshotCatalogEntryV1, ...]
    current_matches: tuple[LearningCorpusCurrentMatchSelectionV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningCorpusCatalogV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        corpus_id: str,
        revision: int,
        match_snapshots: tuple[LearningCorpusMatchSnapshotCatalogEntryV1, ...],
        current_matches: tuple[LearningCorpusCurrentMatchSelectionV1, ...],
    ) -> LearningCorpusCatalogV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_catalog_version",
            LEARNING_CORPUS_CATALOG_VERSION,
        )
        object.__setattr__(value, "corpus_id", corpus_id)
        object.__setattr__(value, "revision", revision)
        object.__setattr__(value, "match_snapshots", match_snapshots)
        object.__setattr__(value, "current_matches", current_matches)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_catalog_version": self.learning_corpus_catalog_version,
            "corpus_id": self.corpus_id,
            "revision": self.revision,
            "match_snapshots": [item.to_dict() for item in self.match_snapshots],
            "current_matches": [item.to_dict() for item in self.current_matches],
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusMatchSnapshotClassificationV1:
    """One non-mutating relationship between a candidate and a Catalog."""

    learning_corpus_snapshot_classification_version: int = (
        LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION
    )
    relation: str
    match_id: str
    candidate_snapshot_id: str
    candidate_workspace_revision: int
    current_snapshot_id: str | None
    current_workspace_revision: int | None
    same_match_snapshot_ids: tuple[str, ...]
    same_revision_snapshot_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusMatchSnapshotClassificationV1 must be constructed by its "
            "focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        relation: str,
        match_id: str,
        candidate_snapshot_id: str,
        candidate_workspace_revision: int,
        current_snapshot_id: str | None,
        current_workspace_revision: int | None,
        same_match_snapshot_ids: tuple[str, ...],
        same_revision_snapshot_ids: tuple[str, ...],
    ) -> LearningCorpusMatchSnapshotClassificationV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_snapshot_classification_version",
                LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION,
            ),
            ("relation", relation),
            ("match_id", match_id),
            ("candidate_snapshot_id", candidate_snapshot_id),
            ("candidate_workspace_revision", candidate_workspace_revision),
            ("current_snapshot_id", current_snapshot_id),
            ("current_workspace_revision", current_workspace_revision),
            ("same_match_snapshot_ids", same_match_snapshot_ids),
            ("same_revision_snapshot_ids", same_revision_snapshot_ids),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_snapshot_classification_version,
            LEARNING_CORPUS_SNAPSHOT_CLASSIFICATION_VERSION,
            "learning_corpus_snapshot_classification_version",
        )
        if self.relation not in LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS:
            raise ValueError(
                "relation must be one canonical Learning Corpus Snapshot relation."
            )
        _require_identifier(self.match_id, "match_id")
        _require_hash(self.candidate_snapshot_id, "candidate_snapshot_id")
        _require_non_negative_integer(
            self.candidate_workspace_revision,
            "candidate_workspace_revision",
        )
        if (self.current_snapshot_id is None) != (
            self.current_workspace_revision is None
        ):
            raise ValueError("Current Snapshot identity and revision must be both present or null.")
        if self.current_snapshot_id is not None:
            _require_hash(self.current_snapshot_id, "current_snapshot_id")
            _require_non_negative_integer(
                self.current_workspace_revision,
                "current_workspace_revision",
            )
        for field_name in ("same_match_snapshot_ids", "same_revision_snapshot_ids"):
            values = getattr(self, field_name)
            if type(values) is not tuple or len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be one unique immutable tuple.")
            for snapshot_id in values:
                _require_hash(snapshot_id, field_name)
        if not set(self.same_revision_snapshot_ids) <= set(self.same_match_snapshot_ids):
            raise ValueError("Same-revision Snapshot IDs must be same-Match Snapshot IDs.")
        if self.relation == "new_match":
            if (
                self.current_snapshot_id is not None
                or self.same_match_snapshot_ids
                or self.same_revision_snapshot_ids
            ):
                raise ValueError("A new Match cannot have existing Snapshot relationships.")
        elif self.current_snapshot_id is None or not self.same_match_snapshot_ids:
            raise ValueError("An existing-Match classification requires a current Snapshot.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_snapshot_classification_version": (
                self.learning_corpus_snapshot_classification_version
            ),
            "relation": self.relation,
            "match_id": self.match_id,
            "candidate_snapshot_id": self.candidate_snapshot_id,
            "candidate_workspace_revision": self.candidate_workspace_revision,
            "current_snapshot_id": self.current_snapshot_id,
            "current_workspace_revision": self.current_workspace_revision,
            "same_match_snapshot_ids": list(self.same_match_snapshot_ids),
            "same_revision_snapshot_ids": list(self.same_revision_snapshot_ids),
        }


def build_learning_corpus_match_snapshot_catalog_entry_v1(
    snapshot: LearningCorpusMatchSnapshotV1,
) -> LearningCorpusMatchSnapshotCatalogEntryV1:
    """Summarizes one validated Snapshot without retaining it in the entry."""
    validate_learning_corpus_match_snapshot_v1(snapshot)
    workspace = snapshot.workspace
    definition = workspace.match_definition
    observed_game_count = 0
    passed_deal_count = 0
    empty_slot_count = 0
    for slot in workspace.slots:
        if slot.slot_kind == "observed_game":
            observed_game_count += 1
        elif slot.slot_kind == "passed_deal":
            passed_deal_count += 1
        else:
            empty_slot_count += 1
    if observed_game_count != len(snapshot.game_references):
        raise ValueError("Catalog observed-Game count does not reconcile with references.")
    return LearningCorpusMatchSnapshotCatalogEntryV1._from_validated(
        match_snapshot_id=snapshot.match_snapshot_id,
        match_id=snapshot.match_id,
        workspace_revision=snapshot.workspace_revision,
        source_workspace_fingerprint=snapshot.source_workspace_fingerprint,
        source_content_fingerprint=snapshot.source_content_fingerprint,
        played_at=definition.played_at,
        source_kind=definition.source.source_kind,
        source_title=definition.source.source_title,
        game_platform=definition.game_platform,
        perspective_player_id=definition.perspective_player_id,
        player_ids=tuple(participant.player_id for participant in definition.participants),
        observed_game_count=observed_game_count,
        passed_deal_count=passed_deal_count,
        empty_slot_count=empty_slot_count,
        decision_count=len(snapshot.decision_references),
        commentary_count=len(snapshot.commentary_references),
        response_link_count=len(snapshot.response_references),
    )


def build_learning_corpus_current_match_selection_v1(
    *,
    match_id: str,
    match_snapshot_id: str,
) -> LearningCorpusCurrentMatchSelectionV1:
    """Builds one explicit current selection without choosing a Snapshot."""
    return LearningCorpusCurrentMatchSelectionV1._from_validated(
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
    )


def _validate_learning_corpus_catalog_v1(catalog: LearningCorpusCatalogV1) -> None:
    _require_version(
        catalog.learning_corpus_catalog_version,
        LEARNING_CORPUS_CATALOG_VERSION,
        "learning_corpus_catalog_version",
    )
    _require_identifier(catalog.corpus_id, "corpus_id")
    _require_non_negative_integer(catalog.revision, "revision")
    for entry in catalog.match_snapshots:
        if type(entry) is not LearningCorpusMatchSnapshotCatalogEntryV1:
            raise ValueError("match_snapshots must contain only Catalog entries.")
        entry._validate()
    for selection in catalog.current_matches:
        if type(selection) is not LearningCorpusCurrentMatchSelectionV1:
            raise ValueError("current_matches must contain only current selections.")
        selection._validate()

    expected_entry_order = tuple(
        sorted(
            catalog.match_snapshots,
            key=lambda item: (
                item.match_id,
                item.workspace_revision,
                item.match_snapshot_id,
            ),
        )
    )
    if catalog.match_snapshots != expected_entry_order:
        raise ValueError("Catalog Snapshot entries must use canonical order.")
    expected_selection_order = tuple(
        sorted(catalog.current_matches, key=lambda item: item.match_id)
    )
    if catalog.current_matches != expected_selection_order:
        raise ValueError("Catalog current selections must use Match-ID order.")

    snapshot_ids = tuple(item.match_snapshot_id for item in catalog.match_snapshots)
    content_fingerprints = tuple(
        item.source_content_fingerprint for item in catalog.match_snapshots
    )
    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise ValueError("Catalog Snapshot IDs must be unique.")
    if len(content_fingerprints) != len(set(content_fingerprints)):
        raise ValueError("Catalog source content fingerprints must be unique.")

    represented_match_ids = {item.match_id for item in catalog.match_snapshots}
    selected_match_ids = tuple(item.match_id for item in catalog.current_matches)
    if len(selected_match_ids) != len(set(selected_match_ids)):
        raise ValueError("Catalog current Match selections must be unique by Match ID.")
    if set(selected_match_ids) != represented_match_ids:
        raise ValueError("Every represented Match requires exactly one current selection.")
    entries_by_snapshot_id = {
        item.match_snapshot_id: item for item in catalog.match_snapshots
    }
    for selection in catalog.current_matches:
        entry = entries_by_snapshot_id.get(selection.match_snapshot_id)
        if entry is None or entry.match_id != selection.match_id:
            raise ValueError("Every current selection must reference an entry of the same Match.")


def build_learning_corpus_catalog_v1(
    *,
    corpus_id: str,
    revision: int,
    match_snapshots: tuple[LearningCorpusMatchSnapshotCatalogEntryV1, ...]
    | list[LearningCorpusMatchSnapshotCatalogEntryV1],
    current_matches: tuple[LearningCorpusCurrentMatchSelectionV1, ...]
    | list[LearningCorpusCurrentMatchSelectionV1],
) -> LearningCorpusCatalogV1:
    """Builds one complete canonically ordered Catalog without mutation behavior."""
    _require_identifier(corpus_id, "corpus_id")
    _require_non_negative_integer(revision, "revision")
    if isinstance(match_snapshots, (str, bytes)) or not isinstance(
        match_snapshots, (list, tuple)
    ):
        raise ValueError("match_snapshots must be an ordered array.")
    if isinstance(current_matches, (str, bytes)) or not isinstance(
        current_matches, (list, tuple)
    ):
        raise ValueError("current_matches must be an ordered array.")
    entries = tuple(match_snapshots)
    selections = tuple(current_matches)
    if any(type(item) is not LearningCorpusMatchSnapshotCatalogEntryV1 for item in entries):
        raise ValueError("match_snapshots must contain only Catalog entries.")
    if any(type(item) is not LearningCorpusCurrentMatchSelectionV1 for item in selections):
        raise ValueError("current_matches must contain only current selections.")
    catalog = LearningCorpusCatalogV1._from_validated(
        corpus_id=corpus_id,
        revision=revision,
        match_snapshots=tuple(
            sorted(
                entries,
                key=lambda item: (
                    item.match_id,
                    item.workspace_revision,
                    item.match_snapshot_id,
                ),
            )
        ),
        current_matches=tuple(sorted(selections, key=lambda item: item.match_id)),
    )
    _validate_learning_corpus_catalog_v1(catalog)
    return catalog


def create_empty_learning_corpus_catalog_v1(corpus_id: str) -> LearningCorpusCatalogV1:
    """Creates one empty revision-zero Catalog with no inferred selections."""
    return build_learning_corpus_catalog_v1(
        corpus_id=corpus_id,
        revision=0,
        match_snapshots=(),
        current_matches=(),
    )


def classify_learning_corpus_match_snapshot_v1(
    catalog: LearningCorpusCatalogV1,
    snapshot: LearningCorpusMatchSnapshotV1,
) -> LearningCorpusMatchSnapshotClassificationV1:
    """Classifies one candidate without choosing, importing, or mutating anything."""
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    _validate_learning_corpus_catalog_v1(catalog)
    validate_learning_corpus_match_snapshot_v1(snapshot)
    same_match_entries = tuple(
        entry for entry in catalog.match_snapshots if entry.match_id == snapshot.match_id
    )
    same_match_snapshot_ids = tuple(
        entry.match_snapshot_id for entry in same_match_entries
    )
    same_revision_entries = tuple(
        entry
        for entry in same_match_entries
        if entry.workspace_revision == snapshot.workspace_revision
    )
    same_revision_snapshot_ids = tuple(
        entry.match_snapshot_id for entry in same_revision_entries
    )

    if not same_match_entries:
        relation = "new_match"
        current_entry = None
    else:
        selection = next(
            item for item in catalog.current_matches if item.match_id == snapshot.match_id
        )
        current_entry = next(
            item
            for item in same_match_entries
            if item.match_snapshot_id == selection.match_snapshot_id
        )
        if snapshot.match_snapshot_id in same_match_snapshot_ids:
            relation = "duplicate_snapshot"
        elif same_revision_entries:
            relation = "same_revision_content_conflict"
        elif snapshot.workspace_revision > current_entry.workspace_revision:
            relation = "newer_revision"
        else:
            relation = "older_revision"

    return LearningCorpusMatchSnapshotClassificationV1._from_validated(
        relation=relation,
        match_id=snapshot.match_id,
        candidate_snapshot_id=snapshot.match_snapshot_id,
        candidate_workspace_revision=snapshot.workspace_revision,
        current_snapshot_id=(
            None if current_entry is None else current_entry.match_snapshot_id
        ),
        current_workspace_revision=(
            None if current_entry is None else current_entry.workspace_revision
        ),
        same_match_snapshot_ids=same_match_snapshot_ids,
        same_revision_snapshot_ids=same_revision_snapshot_ids,
    )
