from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from skat_ai.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_EXPORT_VERSION,
    LearningDatasetPartitionPreparationResultV1,
    _require_hash,
    _require_version,
)
from skat_ai.learning_dataset_v2_partition_identity import (
    build_learning_dataset_partition_export_id_v1,
    build_learning_dataset_partition_plan_fingerprint_v1,
    build_learning_dataset_partitioned_view_fingerprint_v1,
)

LEARNING_DATASET_PARTITION_DOCUMENT_KIND = "skat_ai_learning_dataset_v2_partition_preparation"


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPartitionPreparationExportV1:
    learning_dataset_partition_export_version: int
    document_kind: str
    export_id: str
    request_fingerprint: str
    plan_fingerprint: str
    preparation_result: LearningDatasetPartitionPreparationResultV1

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPartitionPreparationExportV1 requires its builder.")

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningDatasetPartitionPreparationExportV1:
        value = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_partition_export_version,
            LEARNING_DATASET_PARTITION_EXPORT_VERSION,
            "learning_dataset_partition_export_version",
        )
        if self.document_kind != LEARNING_DATASET_PARTITION_DOCUMENT_KIND:
            raise ValueError("document_kind must identify Dataset-v2 partition preparation.")
        for field_name in ("export_id", "request_fingerprint", "plan_fingerprint"):
            _require_hash(getattr(self, field_name), field_name)
        if type(self.preparation_result) is not LearningDatasetPartitionPreparationResultV1:
            raise ValueError("preparation_result must be the exact internal Result.")
        self.preparation_result._validate()
        if self.request_fingerprint != self.preparation_result.request_fingerprint:
            raise ValueError("request_fingerprint must match the preparation Result.")
        if self.plan_fingerprint != self.preparation_result.plan.plan_fingerprint:
            raise ValueError("plan_fingerprint must match the preparation Result.")
        if self.export_id != build_learning_dataset_partition_export_id_v1(self.to_dict()):
            raise ValueError("export_id must cover the exact partition export.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_partition_export_version": (
                self.learning_dataset_partition_export_version
            ),
            "document_kind": self.document_kind,
            "export_id": self.export_id,
            "request_fingerprint": self.request_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "preparation_result": self.preparation_result.to_dict(),
        }


def _validate_result_identities(result: LearningDatasetPartitionPreparationResultV1) -> None:
    plan = result.plan
    if plan.plan_fingerprint != build_learning_dataset_partition_plan_fingerprint_v1(plan):
        raise ValueError("plan_fingerprint must cover the exact Plan.")
    if plan.leakage_audit is not None and plan.leakage_audit.plan_fingerprint != (
        plan.plan_fingerprint
    ):
        raise ValueError("Leakage Audit must reference the exact Plan.")
    if (
        result.partitioned_view is not None
        and result.partitioned_view.partitioned_view_fingerprint
        != (build_learning_dataset_partitioned_view_fingerprint_v1(result.partitioned_view))
    ):
        raise ValueError("partitioned_view_fingerprint must cover the exact view.")


def build_learning_dataset_partition_preparation_export_v1(
    result: LearningDatasetPartitionPreparationResultV1,
) -> LearningDatasetPartitionPreparationExportV1:
    """Wraps one already-prepared Result without rerunning preparation."""
    if type(result) is not LearningDatasetPartitionPreparationResultV1:
        raise ValueError("result must be an exact partition preparation Result.")
    result._validate()
    _validate_result_identities(result)
    values = {
        "learning_dataset_partition_export_version": (LEARNING_DATASET_PARTITION_EXPORT_VERSION),
        "document_kind": LEARNING_DATASET_PARTITION_DOCUMENT_KIND,
        "export_id": "0" * 64,
        "request_fingerprint": result.request_fingerprint,
        "plan_fingerprint": result.plan.plan_fingerprint,
        "preparation_result": result.to_dict(),
    }
    export_id = build_learning_dataset_partition_export_id_v1(values)
    return LearningDatasetPartitionPreparationExportV1._from_validated(
        learning_dataset_partition_export_version=(LEARNING_DATASET_PARTITION_EXPORT_VERSION),
        document_kind=LEARNING_DATASET_PARTITION_DOCUMENT_KIND,
        export_id=export_id,
        request_fingerprint=result.request_fingerprint,
        plan_fingerprint=result.plan.plan_fingerprint,
        preparation_result=result,
    )


def serialize_learning_dataset_partition_preparation_export_v1(
    export: LearningDatasetPartitionPreparationExportV1,
) -> bytes:
    """Returns deterministic private UTF-8 bytes without accepting a path."""
    if type(export) is not LearningDatasetPartitionPreparationExportV1:
        raise ValueError("export must be an exact partition preparation Export.")
    export._validate()
    return (
        json.dumps(
            export.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
