from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from skatmind.learning_corpus_catalog import (
    LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS,
    LearningCorpusCatalogV1,
    LearningCorpusMatchSnapshotClassificationV1,
    _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1,
    _validate_learning_corpus_catalog_v1,
)
from skatmind.learning_corpus_match_snapshot import (
    LearningCorpusMatchSnapshotV1,
    validate_learning_corpus_match_snapshot_v1,
)

LEARNING_CORPUS_PERSISTENCE_VERSION = 1
LEARNING_CORPUS_STORE_VERSION = 1
LEARNING_CORPUS_CATALOG_CHANGE_VERSION = 1
LEARNING_CORPUS_IMPORT_VERSION = 1

LEARNING_CORPUS_CATALOG_DOCUMENT_KIND = "skatmind_learning_corpus_catalog"
LEGACY_LEARNING_CORPUS_CATALOG_DOCUMENT_KIND = "skat_ai_learning_corpus_catalog"
LEARNING_CORPUS_SUPPORTED_CATALOG_DOCUMENT_KINDS = (
    LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    LEGACY_LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
)
LEARNING_CORPUS_CATALOG_FILENAME = "catalog.json"
LEARNING_CORPUS_OBJECTS_DIRECTORY = "objects"
LEARNING_CORPUS_MATCH_SNAPSHOT_OBJECT_DIRECTORY = "match_workspace_snapshot"
LEARNING_CORPUS_OBJECT_FILE_SUFFIX = ".json"
LEARNING_CORPUS_PERSISTENCE_ENCODING = "utf-8"

LEARNING_CORPUS_WRITE_STATUSES: Final[tuple[str, ...]] = (
    "saved",
    "unchanged",
    "conflict",
)
LEARNING_CORPUS_OBJECT_WRITE_STATUSES: Final[tuple[str, ...]] = (
    "saved",
    "unchanged",
    "not_required",
)
LEARNING_CORPUS_CATALOG_CHANGE_OPERATIONS: Final[tuple[str, ...]] = (
    "import_match_snapshot",
    "select_current_snapshot",
)
LEARNING_CORPUS_CATALOG_CHANGE_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
    "resolution_required",
)
LEARNING_CORPUS_STORE_OPERATION_STATUSES: Final[tuple[str, ...]] = (
    "applied",
    "unchanged",
    "revision_conflict",
    "persistence_conflict",
    "resolution_required",
)
LEARNING_CORPUS_IMPORT_SELECTION_MODES: Final[tuple[str, ...]] = (
    "select_imported",
    "keep_current",
)
LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS: Final[tuple[str, ...]] = (
    "reject",
    "retain",
)

LEARNING_CORPUS_LAYOUT_POLICY = "explicit_root_catalog_and_content_addressed_objects"
LEARNING_CORPUS_CATALOG_FINGERPRINT_POLICY = (
    "sha256_canonical_learning_corpus_catalog_v1"
)
LEARNING_CORPUS_CONTENT_FINGERPRINT_POLICY = (
    "sha256_canonical_document_without_content_fingerprint"
)
LEARNING_CORPUS_CONFLICT_POLICY = (
    "expected_catalog_content_fingerprint_compare_and_swap"
)
LEARNING_CORPUS_OBJECT_WRITE_POLICY = "immutable_no_clobber_content_addressed_publish"
LEARNING_CORPUS_CATALOG_WRITE_POLICY = "same_directory_temp_file_atomic_replace"
LEARNING_CORPUS_RESUME_POLICY = "strict_catalog_and_referenced_object_validation"
LEARNING_CORPUS_IMPORT_POLICY = "strict_workspace_file_to_immutable_match_snapshot"
LEARNING_CORPUS_ORPHAN_POLICY = (
    "catalog_authoritative_unreferenced_objects_reported_not_deleted"
)
LEARNING_CORPUS_SELECTION_UPDATE_POLICY = "explicit_select_imported_or_keep_current"


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
        raise ValueError(
            f"{field_name} must be a non-empty, non-padded string{nullable}."
        )
    return value


def _require_fingerprint(
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
        raise ValueError(
            f"{field_name} must be a lowercase SHA-256 hexadecimal value{nullable}."
        )
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _require_exact_catalog(catalog: object) -> LearningCorpusCatalogV1:
    if type(catalog) is not LearningCorpusCatalogV1:
        raise ValueError("catalog must be an exact LearningCorpusCatalogV1.")
    _validate_learning_corpus_catalog_v1(catalog)
    return catalog


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusCatalogPersistenceDocumentV1:
    """One immutable authoritative Learning Corpus Catalog document."""

    learning_corpus_persistence_version: int = LEARNING_CORPUS_PERSISTENCE_VERSION
    document_kind: str = LEARNING_CORPUS_CATALOG_DOCUMENT_KIND
    catalog_fingerprint: str
    content_fingerprint: str
    catalog: LearningCorpusCatalogV1

    def __post_init__(self) -> None:
        self._validate_structure(validate_catalog=True)
        from skatmind.learning_corpus_persistence_codec import (
            _validate_learning_corpus_catalog_persistence_document_fingerprints_v1,
        )

        _validate_learning_corpus_catalog_persistence_document_fingerprints_v1(self)

    def _validate_structure(self, *, validate_catalog: bool) -> None:
        _require_version(
            self.learning_corpus_persistence_version,
            LEARNING_CORPUS_PERSISTENCE_VERSION,
            "learning_corpus_persistence_version",
        )
        if self.document_kind not in LEARNING_CORPUS_SUPPORTED_CATALOG_DOCUMENT_KINDS:
            raise ValueError(
                "document_kind must be one supported Learning Corpus Catalog kind."
            )
        _require_fingerprint(self.catalog_fingerprint, "catalog_fingerprint")
        _require_fingerprint(self.content_fingerprint, "content_fingerprint")
        if type(self.catalog) is not LearningCorpusCatalogV1:
            raise ValueError("catalog must be a LearningCorpusCatalogV1.")
        if validate_catalog:
            _validate_learning_corpus_catalog_v1(self.catalog)

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_persistence_version": (
                self.learning_corpus_persistence_version
            ),
            "document_kind": self.document_kind,
            "catalog_fingerprint": self.catalog_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "catalog": self.catalog.to_dict(),
        }


def _build_verified_learning_corpus_catalog_persistence_document_v1(
    *,
    learning_corpus_persistence_version: int = LEARNING_CORPUS_PERSISTENCE_VERSION,
    document_kind: str = LEARNING_CORPUS_CATALOG_DOCUMENT_KIND,
    catalog_fingerprint: str,
    content_fingerprint: str,
    catalog: LearningCorpusCatalogV1,
) -> LearningCorpusCatalogPersistenceDocumentV1:
    document = object.__new__(LearningCorpusCatalogPersistenceDocumentV1)
    object.__setattr__(
        document,
        "learning_corpus_persistence_version",
        learning_corpus_persistence_version,
    )
    object.__setattr__(document, "document_kind", document_kind)
    object.__setattr__(document, "catalog_fingerprint", catalog_fingerprint)
    object.__setattr__(document, "content_fingerprint", content_fingerprint)
    object.__setattr__(document, "catalog", catalog)
    document._validate_structure(validate_catalog=False)
    return document


def _validate_store_snapshots(
    *,
    document: LearningCorpusCatalogPersistenceDocumentV1,
    match_snapshots: tuple[LearningCorpusMatchSnapshotV1, ...],
) -> None:
    entries = document.catalog.match_snapshots
    if len(match_snapshots) != len(entries):
        raise ValueError("match_snapshots must correspond one-for-one with Catalog entries.")
    for entry, snapshot in zip(entries, match_snapshots, strict=True):
        if type(snapshot) is not LearningCorpusMatchSnapshotV1:
            raise ValueError(
                "match_snapshots must contain only LearningCorpusMatchSnapshotV1 values."
            )
        validate_learning_corpus_match_snapshot_v1(snapshot)
        if (
            _build_learning_corpus_match_snapshot_catalog_entry_from_validated_v1(
                snapshot
            )
            != entry
        ):
            raise ValueError("Each Match Snapshot must reconcile with its Catalog entry.")


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusStoreResumeResultV1:
    """One strict path-free Resume result for the authoritative Corpus Store."""

    learning_corpus_store_version: int = LEARNING_CORPUS_STORE_VERSION
    document: LearningCorpusCatalogPersistenceDocumentV1
    match_snapshots: tuple[LearningCorpusMatchSnapshotV1, ...]
    orphan_match_snapshot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        self._validate_structure(validate_snapshots=True)

    def _validate_structure(self, *, validate_snapshots: bool) -> None:
        _require_version(
            self.learning_corpus_store_version,
            LEARNING_CORPUS_STORE_VERSION,
            "learning_corpus_store_version",
        )
        if type(self.document) is not LearningCorpusCatalogPersistenceDocumentV1:
            raise ValueError(
                "document must be a LearningCorpusCatalogPersistenceDocumentV1."
            )
        if type(self.match_snapshots) is not tuple:
            raise ValueError("match_snapshots must be an immutable tuple.")
        if validate_snapshots:
            _validate_store_snapshots(
                document=self.document,
                match_snapshots=self.match_snapshots,
            )
        if type(self.orphan_match_snapshot_ids) is not tuple:
            raise ValueError("orphan_match_snapshot_ids must be an immutable tuple.")
        for snapshot_id in self.orphan_match_snapshot_ids:
            _require_fingerprint(snapshot_id, "orphan_match_snapshot_ids")
        if self.orphan_match_snapshot_ids != tuple(
            sorted(set(self.orphan_match_snapshot_ids))
        ):
            raise ValueError("Orphan Match Snapshot IDs must be unique and sorted.")
        referenced_ids = {
            entry.match_snapshot_id for entry in self.document.catalog.match_snapshots
        }
        if referenced_ids.intersection(self.orphan_match_snapshot_ids):
            raise ValueError("A Catalog-referenced Match Snapshot cannot be an orphan.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_store_version": self.learning_corpus_store_version,
            "document": self.document.to_dict(),
            "match_snapshots": [snapshot.to_dict() for snapshot in self.match_snapshots],
            "orphan_match_snapshot_ids": list(self.orphan_match_snapshot_ids),
        }


def _build_verified_learning_corpus_store_resume_result_v1(
    *,
    document: LearningCorpusCatalogPersistenceDocumentV1,
    match_snapshots: tuple[LearningCorpusMatchSnapshotV1, ...],
    orphan_match_snapshot_ids: tuple[str, ...],
) -> LearningCorpusStoreResumeResultV1:
    result = object.__new__(LearningCorpusStoreResumeResultV1)
    object.__setattr__(result, "learning_corpus_store_version", LEARNING_CORPUS_STORE_VERSION)
    object.__setattr__(result, "document", document)
    object.__setattr__(result, "match_snapshots", match_snapshots)
    object.__setattr__(result, "orphan_match_snapshot_ids", orphan_match_snapshot_ids)
    result._validate_structure(validate_snapshots=False)
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusCatalogChangeResultV1:
    """One immutable pure Catalog mutation outcome."""

    learning_corpus_catalog_change_version: int = LEARNING_CORPUS_CATALOG_CHANGE_VERSION
    operation: str
    status: str
    relation: str | None
    selection_mode: str | None
    same_revision_resolution: str | None
    match_id: str | None
    match_snapshot_id: str | None
    expected_revision: int
    source_revision: int
    current_revision: int
    snapshot_added: bool
    selection_changed: bool
    previous_current_snapshot_id: str | None
    current_snapshot_id: str | None
    catalog: LearningCorpusCatalogV1

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_catalog_change_version,
            LEARNING_CORPUS_CATALOG_CHANGE_VERSION,
            "learning_corpus_catalog_change_version",
        )
        if self.operation not in LEARNING_CORPUS_CATALOG_CHANGE_OPERATIONS:
            raise ValueError("operation must be one canonical Catalog Change operation.")
        if self.status not in LEARNING_CORPUS_CATALOG_CHANGE_STATUSES:
            raise ValueError("status must be one canonical Catalog Change status.")
        if self.relation is not None and self.relation not in (
            LEARNING_CORPUS_MATCH_SNAPSHOT_RELATIONS
        ):
            raise ValueError("relation must be null or one canonical Snapshot relation.")
        if self.operation == "import_match_snapshot":
            if self.selection_mode not in LEARNING_CORPUS_IMPORT_SELECTION_MODES:
                raise ValueError("An import requires one canonical selection_mode.")
            if self.same_revision_resolution not in (
                LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS
            ):
                raise ValueError(
                    "An import requires one canonical same_revision_resolution."
                )
        elif self.selection_mode is not None or self.same_revision_resolution is not None:
            raise ValueError("Selection mode and resolution are present only for import.")
        if (self.match_id is None) != (self.match_snapshot_id is None):
            raise ValueError("Match and Snapshot identities must be both present or null.")
        _require_identifier(self.match_id, "match_id", allow_none=True)
        _require_fingerprint(
            self.match_snapshot_id,
            "match_snapshot_id",
            allow_none=True,
        )
        for field_name in ("expected_revision", "source_revision", "current_revision"):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        _require_boolean(self.snapshot_added, "snapshot_added")
        _require_boolean(self.selection_changed, "selection_changed")
        _require_fingerprint(
            self.previous_current_snapshot_id,
            "previous_current_snapshot_id",
            allow_none=True,
        )
        _require_fingerprint(
            self.current_snapshot_id,
            "current_snapshot_id",
            allow_none=True,
        )
        _require_exact_catalog(self.catalog)
        if self.catalog.revision != self.current_revision:
            raise ValueError("Catalog revision must equal current_revision.")

        changed = self.snapshot_added or self.selection_changed
        if self.status == "applied":
            if self.expected_revision != self.source_revision:
                raise ValueError("An applied Change requires the expected source revision.")
            if self.current_revision != self.source_revision + 1:
                raise ValueError("An applied Change increments the Catalog revision once.")
            if not changed:
                raise ValueError("An applied Change must add a Snapshot or change selection.")
        elif self.status == "unchanged":
            if self.expected_revision != self.source_revision:
                raise ValueError("An unchanged Change requires the expected source revision.")
            if self.current_revision != self.source_revision or changed:
                raise ValueError("An unchanged Change preserves revision and content.")
        elif self.status == "revision_conflict":
            if self.expected_revision == self.source_revision:
                raise ValueError("A revision conflict requires a stale expected revision.")
            if self.current_revision != self.source_revision or changed:
                raise ValueError("A revision conflict preserves the source Catalog.")
            if self.relation is not None:
                raise ValueError("A revision conflict precedes Snapshot classification.")
        else:
            if self.expected_revision != self.source_revision:
                raise ValueError("Resolution-required uses the expected source revision.")
            if self.current_revision != self.source_revision or changed:
                raise ValueError("Resolution-required preserves the source Catalog.")
            if (
                self.relation != "same_revision_content_conflict"
                or self.same_revision_resolution != "reject"
            ):
                raise ValueError(
                    "Resolution-required is only the rejected same-revision conflict."
                )

        if self.operation == "select_current_snapshot" and self.relation is not None:
            raise ValueError("Current-selection operations do not classify a Snapshot.")
        if self.operation == "select_current_snapshot" and self.snapshot_added:
            raise ValueError("Current-selection operations cannot add Snapshot entries.")
        if (
            self.operation == "import_match_snapshot"
            and self.status not in ("revision_conflict",)
            and self.relation is None
        ):
            raise ValueError("A semantic import Change requires its Snapshot relation.")
        if self.status != "revision_conflict" and self.match_id is None:
            raise ValueError("A semantic Catalog Change requires Match and Snapshot IDs.")

        if self.status != "revision_conflict":
            if self.status != "resolution_required":
                entries = {
                    item.match_snapshot_id: item
                    for item in self.catalog.match_snapshots
                }
                candidate_entry = entries.get(self.match_snapshot_id)
                if candidate_entry is None or candidate_entry.match_id != self.match_id:
                    raise ValueError(
                        "The returned Catalog must retain the requested Match Snapshot."
                    )
            selection = next(
                (
                    item
                    for item in self.catalog.current_matches
                    if item.match_id == self.match_id
                ),
                None,
            )
            if selection is None or selection.match_snapshot_id != self.current_snapshot_id:
                raise ValueError(
                    "current_snapshot_id must equal the returned Catalog selection."
                )
            if self.selection_changed != (
                self.previous_current_snapshot_id != self.current_snapshot_id
            ):
                raise ValueError(
                    "selection_changed must match the previous and current identities."
                )
        elif (
            self.previous_current_snapshot_id is not None
            or self.current_snapshot_id is not None
        ):
            raise ValueError(
                "A revision conflict does not evaluate Current-selection identities."
            )
        if self.operation == "import_match_snapshot" and self.status != "revision_conflict":
            if self.relation == "new_match":
                if (
                    not self.snapshot_added
                    or not self.selection_changed
                    or self.previous_current_snapshot_id is not None
                    or self.current_snapshot_id != self.match_snapshot_id
                ):
                    raise ValueError("A new Match adds and selects its first Snapshot.")
            elif self.relation == "duplicate_snapshot":
                if self.snapshot_added:
                    raise ValueError("A duplicate Snapshot cannot add a Catalog entry.")
            elif self.relation in ("newer_revision", "older_revision"):
                if not self.snapshot_added:
                    raise ValueError("A new Workspace revision must add its Snapshot entry.")
            elif self.relation == "same_revision_content_conflict":
                expected_added = self.same_revision_resolution == "retain"
                if self.snapshot_added != expected_added:
                    raise ValueError(
                        "Same-revision Snapshot retention must match explicit resolution."
                    )
            if (
                self.relation != "new_match"
                and self.selection_mode == "keep_current"
                and self.selection_changed
            ):
                raise ValueError("keep_current cannot change an existing Match selection.")
            if (
                self.selection_mode == "select_imported"
                and self.status == "applied"
                and self.current_snapshot_id != self.match_snapshot_id
            ):
                raise ValueError("select_imported must select the candidate Snapshot.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_catalog_change_version": (
                self.learning_corpus_catalog_change_version
            ),
            "operation": self.operation,
            "status": self.status,
            "relation": self.relation,
            "selection_mode": self.selection_mode,
            "same_revision_resolution": self.same_revision_resolution,
            "match_id": self.match_id,
            "match_snapshot_id": self.match_snapshot_id,
            "expected_revision": self.expected_revision,
            "source_revision": self.source_revision,
            "current_revision": self.current_revision,
            "snapshot_added": self.snapshot_added,
            "selection_changed": self.selection_changed,
            "previous_current_snapshot_id": self.previous_current_snapshot_id,
            "current_snapshot_id": self.current_snapshot_id,
            "catalog": self.catalog.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusCatalogWriteResultV1:
    """One normal saved, unchanged, or optimistic Catalog conflict outcome."""

    learning_corpus_persistence_version: int = LEARNING_CORPUS_PERSISTENCE_VERSION
    status: str
    corpus_id: str
    revision: int
    expected_content_fingerprint: str | None
    existing_content_fingerprint: str | None
    requested_content_fingerprint: str

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_persistence_version,
            LEARNING_CORPUS_PERSISTENCE_VERSION,
            "learning_corpus_persistence_version",
        )
        if self.status not in LEARNING_CORPUS_WRITE_STATUSES:
            raise ValueError("status must be one canonical Learning Corpus write status.")
        _require_identifier(self.corpus_id, "corpus_id")
        _require_non_negative_integer(self.revision, "revision")
        _require_fingerprint(
            self.expected_content_fingerprint,
            "expected_content_fingerprint",
            allow_none=True,
        )
        _require_fingerprint(
            self.existing_content_fingerprint,
            "existing_content_fingerprint",
            allow_none=True,
        )
        _require_fingerprint(
            self.requested_content_fingerprint,
            "requested_content_fingerprint",
        )
        if self.status == "saved":
            if self.expected_content_fingerprint != self.existing_content_fingerprint:
                raise ValueError("A saved Result requires the expected existing fingerprint.")
            if (
                self.existing_content_fingerprint is not None
                and self.requested_content_fingerprint
                == self.existing_content_fingerprint
            ):
                raise ValueError("Equal existing and requested content is unchanged.")
        elif self.status == "unchanged":
            if (
                self.expected_content_fingerprint is None
                or self.expected_content_fingerprint
                != self.existing_content_fingerprint
                or self.expected_content_fingerprint
                != self.requested_content_fingerprint
            ):
                raise ValueError(
                    "An unchanged Result requires three equal non-null fingerprints."
                )
        elif self.expected_content_fingerprint == self.existing_content_fingerprint:
            raise ValueError(
                "A conflict Result requires different expected and existing fingerprints."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_persistence_version": (
                self.learning_corpus_persistence_version
            ),
            "status": self.status,
            "corpus_id": self.corpus_id,
            "revision": self.revision,
            "expected_content_fingerprint": self.expected_content_fingerprint,
            "existing_content_fingerprint": self.existing_content_fingerprint,
            "requested_content_fingerprint": self.requested_content_fingerprint,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusWorkspaceImportResultV1:
    """One path-free strict Workspace-file import outcome."""

    learning_corpus_import_version: int = LEARNING_CORPUS_IMPORT_VERSION
    status: str
    selection_mode: str
    same_revision_resolution: str
    classification: LearningCorpusMatchSnapshotClassificationV1 | None
    catalog_change: LearningCorpusCatalogChangeResultV1 | None
    object_write_status: str
    catalog_write_status: str
    store: LearningCorpusStoreResumeResultV1

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_import_version,
            LEARNING_CORPUS_IMPORT_VERSION,
            "learning_corpus_import_version",
        )
        if self.status not in LEARNING_CORPUS_STORE_OPERATION_STATUSES:
            raise ValueError("status must be one canonical Store-operation status.")
        if self.selection_mode not in LEARNING_CORPUS_IMPORT_SELECTION_MODES:
            raise ValueError("selection_mode must be one canonical import mode.")
        if self.same_revision_resolution not in (
            LEARNING_CORPUS_SAME_REVISION_RESOLUTIONS
        ):
            raise ValueError("same_revision_resolution must be reject or retain.")
        if (
            self.classification is not None
            and type(self.classification)
            is not LearningCorpusMatchSnapshotClassificationV1
        ):
            raise ValueError("classification must be a Snapshot classification or null.")
        if (
            self.catalog_change is not None
            and type(self.catalog_change) is not LearningCorpusCatalogChangeResultV1
        ):
            raise ValueError("catalog_change must be a Catalog Change or null.")
        if self.object_write_status not in LEARNING_CORPUS_OBJECT_WRITE_STATUSES:
            raise ValueError("object_write_status must be canonical.")
        if self.catalog_write_status not in (
            *LEARNING_CORPUS_WRITE_STATUSES,
            "not_required",
        ):
            raise ValueError("catalog_write_status must be canonical or not_required.")
        if type(self.store) is not LearningCorpusStoreResumeResultV1:
            raise ValueError("store must be a LearningCorpusStoreResumeResultV1.")
        if self.classification is not None and self.catalog_change is not None:
            if (
                self.classification.relation != self.catalog_change.relation
                or self.classification.match_id != self.catalog_change.match_id
                or self.classification.candidate_snapshot_id
                != self.catalog_change.match_snapshot_id
            ):
                raise ValueError(
                    "Classification and Catalog Change must describe the same import."
                )
        if self.status == "revision_conflict":
            if self.classification is not None:
                raise ValueError("Revision conflict must precede source classification.")
            if self.catalog_change is None or self.catalog_change.status != self.status:
                raise ValueError("Revision conflict requires its Catalog Change.")
            if (
                self.object_write_status != "not_required"
                or self.catalog_write_status != "not_required"
            ):
                raise ValueError("Revision conflict performs no persistence write.")
        elif self.status == "resolution_required":
            if self.classification is None:
                raise ValueError("Resolution-required must retain classification.")
            if self.catalog_change is None or self.catalog_change.status != self.status:
                raise ValueError("Resolution-required requires its Catalog Change.")
            if (
                self.object_write_status != "not_required"
                or self.catalog_write_status != "not_required"
            ):
                raise ValueError("Resolution-required performs no persistence write.")
        elif self.status == "unchanged":
            if self.classification is None:
                raise ValueError("Unchanged import must retain classification.")
            if self.catalog_change is None or self.catalog_change.status != self.status:
                raise ValueError("Unchanged import requires its Catalog Change.")
            if (
                self.object_write_status != "not_required"
                or self.catalog_write_status != "not_required"
            ):
                raise ValueError("Unchanged import performs no persistence write.")
        elif self.status == "applied":
            if self.classification is None:
                raise ValueError("Applied import must retain classification.")
            if self.catalog_change is None or self.catalog_change.status != self.status:
                raise ValueError("Applied import requires its Catalog Change.")
            if self.catalog_write_status not in ("saved", "unchanged"):
                raise ValueError("Applied import requires a published Catalog.")
        else:
            if self.catalog_change is None:
                if self.classification is not None:
                    raise ValueError(
                        "A pre-semantic persistence conflict has no classification."
                    )
                if (
                    self.object_write_status != "not_required"
                    or self.catalog_write_status != "not_required"
                ):
                    raise ValueError(
                        "A pre-semantic persistence conflict performs no write."
                    )
            else:
                if self.classification is None or self.catalog_change.status != "applied":
                    raise ValueError(
                        "A post-object persistence conflict retains its semantic change."
                    )
                if self.catalog_write_status != "conflict":
                    raise ValueError(
                        "A post-object persistence conflict requires Catalog conflict."
                    )
        if self.catalog_change is not None and self.catalog_change.snapshot_added:
            if self.object_write_status not in ("saved", "unchanged"):
                raise ValueError("A new Catalog entry requires object publication.")
        elif self.object_write_status != "not_required":
            raise ValueError("Object publication is required only for a new Catalog entry.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_import_version": self.learning_corpus_import_version,
            "status": self.status,
            "selection_mode": self.selection_mode,
            "same_revision_resolution": self.same_revision_resolution,
            "classification": (
                None if self.classification is None else self.classification.to_dict()
            ),
            "catalog_change": (
                None if self.catalog_change is None else self.catalog_change.to_dict()
            ),
            "object_write_status": self.object_write_status,
            "catalog_write_status": self.catalog_write_status,
            "store": self.store.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusCurrentSelectionUpdateResultV1:
    """One focused persisted Current-selection operation outcome."""

    learning_corpus_store_version: int = LEARNING_CORPUS_STORE_VERSION
    status: str
    catalog_change: LearningCorpusCatalogChangeResultV1 | None
    catalog_write_status: str
    store: LearningCorpusStoreResumeResultV1

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_store_version,
            LEARNING_CORPUS_STORE_VERSION,
            "learning_corpus_store_version",
        )
        if self.status not in LEARNING_CORPUS_STORE_OPERATION_STATUSES:
            raise ValueError("status must be one canonical Store-operation status.")
        if self.status == "resolution_required":
            raise ValueError("Current selection cannot require Snapshot resolution.")
        if (
            self.catalog_change is not None
            and type(self.catalog_change) is not LearningCorpusCatalogChangeResultV1
        ):
            raise ValueError("catalog_change must be a Catalog Change or null.")
        if self.catalog_write_status not in (
            *LEARNING_CORPUS_WRITE_STATUSES,
            "not_required",
        ):
            raise ValueError("catalog_write_status must be canonical or not_required.")
        if type(self.store) is not LearningCorpusStoreResumeResultV1:
            raise ValueError("store must be a LearningCorpusStoreResumeResultV1.")
        if self.status in ("applied", "unchanged", "revision_conflict"):
            if self.catalog_change is None or self.catalog_change.status != self.status:
                raise ValueError("Selection status must match its Catalog Change.")
        elif self.catalog_change is not None and self.catalog_change.status != "applied":
            raise ValueError(
                "A post-Change persistence conflict retains one applied Catalog Change."
            )
        if self.status == "applied" and self.catalog_write_status not in (
            "saved",
            "unchanged",
        ):
            raise ValueError("An applied selection requires a published Catalog.")
        if self.status in ("unchanged", "revision_conflict") and (
            self.catalog_write_status != "not_required"
        ):
            raise ValueError("Unchanged and revision-conflict selections do not write.")
        if self.status == "persistence_conflict":
            if self.catalog_change is None:
                if self.catalog_write_status != "not_required":
                    raise ValueError("A pre-semantic conflict performs no Catalog Save.")
            elif self.catalog_write_status != "conflict":
                raise ValueError("A post-Change conflict requires Catalog conflict.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_store_version": self.learning_corpus_store_version,
            "status": self.status,
            "catalog_change": (
                None if self.catalog_change is None else self.catalog_change.to_dict()
            ),
            "catalog_write_status": self.catalog_write_status,
            "store": self.store.to_dict(),
        }
