from __future__ import annotations

import hashlib
from typing import Any

from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_player_catalog import LearningCorpusPlayerCatalogV1
from skatmind.learning_dataset_v2_contracts import LearningDatasetV2
from skatmind.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_MATCH_GROUP_VERSION,
    LEARNING_DATASET_PARTITION_PREPARATION_VERSION,
    LEARNING_DATASET_PLAYER_COMPONENT_VERSION,
    LearningDatasetMatchGroupV1,
    LearningDatasetPartitionedViewV1,
    LearningDatasetPartitionLeakageAuditV1,
    LearningDatasetPartitionPlanV1,
    LearningDatasetPartitionPreparationRequestV1,
    LearningDatasetPartitionWeightsV1,
    LearningDatasetPlayerComponentV1,
    _require_hash,
    _require_identifier,
)

LEARNING_DATASET_PARTITION_SOURCE_IDENTITY_DOMAIN = (
    b"skatmind\0learning_dataset_v2_partition_source_identity_v1\0"
)
LEARNING_DATASET_PARTITION_SOURCE_CONTENT_DOMAIN = (
    b"skatmind\0learning_dataset_v2_partition_source_content_v1\0"
)
LEARNING_DATASET_PARTITION_REQUEST_DOMAIN = b"skatmind\0learning_dataset_v2_partition_request_v1\0"
LEARNING_DATASET_MATCH_GROUP_ID_DOMAIN = b"skatmind\0learning_dataset_v2_match_group_v1\0"
LEARNING_DATASET_PLAYER_COMPONENT_ID_DOMAIN = b"skatmind\0learning_dataset_v2_player_component_v1\0"
LEARNING_DATASET_PARTITION_PLAN_FINGERPRINT_DOMAIN = (
    b"skatmind\0learning_dataset_v2_partition_plan_v1\0"
)
LEARNING_DATASET_PARTITION_AUDIT_FINGERPRINT_DOMAIN = (
    b"skatmind\0learning_dataset_v2_partition_audit_v1\0"
)
LEARNING_DATASET_PARTITIONED_VIEW_FINGERPRINT_DOMAIN = (
    b"skatmind\0learning_dataset_v2_partitioned_view_v1\0"
)
LEARNING_DATASET_PARTITION_EXPORT_ID_DOMAIN = b"skatmind\0learning_dataset_v2_partition_export_v1\0"

LEARNING_DATASET_KNOWN_PLAYER_SEED_DOMAIN = "learning_dataset_v2_known_player_split_v1"
LEARNING_DATASET_UNSEEN_PLAYER_SEED_DOMAIN = "learning_dataset_v2_unseen_player_split_v1"

_SEED_DOMAIN_BY_MODE = {
    "known_player": LEARNING_DATASET_KNOWN_PLAYER_SEED_DOMAIN,
    "unseen_player": LEARNING_DATASET_UNSEEN_PLAYER_SEED_DOMAIN,
}


def _identifier(domain: bytes, material: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(material)
    ).hexdigest()


def build_learning_dataset_match_group_id_v1(
    *,
    match_snapshot_id: str,
    match_id: str,
    played_at: str | None,
    player_ids: tuple[str, ...],
    record_ids: tuple[str, ...],
    skipped_decision_ids: tuple[str, ...],
) -> str:
    """Identifies one split-safe Match group without evidence contents."""
    return _identifier(
        LEARNING_DATASET_MATCH_GROUP_ID_DOMAIN,
        {
            "learning_dataset_match_group_version": LEARNING_DATASET_MATCH_GROUP_VERSION,
            "match_snapshot_id": match_snapshot_id,
            "match_id": match_id,
            "played_at": played_at,
            "player_ids": sorted(player_ids),
            "record_ids": list(record_ids),
            "skipped_decision_ids": list(skipped_decision_ids),
        },
    )


def build_learning_dataset_player_component_id_v1(
    *,
    match_snapshot_ids: tuple[str, ...],
    player_ids: tuple[str, ...],
) -> str:
    """Identifies one transitive component from IDs only."""
    return _identifier(
        LEARNING_DATASET_PLAYER_COMPONENT_ID_DOMAIN,
        {
            "learning_dataset_player_component_version": (
                LEARNING_DATASET_PLAYER_COMPONENT_VERSION
            ),
            "match_snapshot_ids": sorted(match_snapshot_ids),
            "player_ids": sorted(player_ids),
        },
    )


def build_learning_dataset_partition_source_identity_fingerprint_v1(
    *,
    mode: str,
    dataset: LearningDatasetV2,
    active_match_groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive_current_match_snapshot_ids: tuple[str, ...],
) -> str:
    """Fingerprints only stable facts permitted to influence assignment."""
    groups = sorted(
        (
            {
                "match_group_id": group.match_group_id,
                "match_snapshot_id": group.match_snapshot_id,
                "match_id": group.match_id,
                "played_at": group.played_at,
                "player_ids": list(group.player_ids),
                "record_ids": list(group.record_ids),
                "skipped_decision_ids": list(group.skipped_decision_ids),
            }
            for group in active_match_groups
        ),
        key=lambda item: (item["match_id"], item["match_snapshot_id"]),
    )
    return _identifier(
        LEARNING_DATASET_PARTITION_SOURCE_IDENTITY_DOMAIN,
        {
            "learning_dataset_partition_preparation_version": (
                LEARNING_DATASET_PARTITION_PREPARATION_VERSION
            ),
            "mode": mode,
            "dataset_id": dataset.dataset_id,
            "learning_dataset_version": dataset.learning_dataset_version,
            "current_match_snapshot_ids": sorted(dataset.current_match_snapshot_ids),
            "active_match_groups": groups,
            "inactive_current_match_snapshot_ids": sorted(inactive_current_match_snapshot_ids),
            "active_match_group_count": len(active_match_groups),
            "record_count": dataset.record_count,
        },
    )


def build_learning_dataset_partition_source_content_fingerprint_v1(
    *,
    mode: str,
    dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
    active_match_groups: tuple[LearningDatasetMatchGroupV1, ...],
    inactive_current_match_snapshot_ids: tuple[str, ...],
) -> str:
    """Fingerprints exact source content without making it assignment input."""
    return _identifier(
        LEARNING_DATASET_PARTITION_SOURCE_CONTENT_DOMAIN,
        {
            "learning_dataset_partition_preparation_version": (
                LEARNING_DATASET_PARTITION_PREPARATION_VERSION
            ),
            "mode": mode,
            "dataset_fingerprint": dataset.dataset_fingerprint,
            "player_catalog_fingerprint": player_catalog.player_catalog_fingerprint,
            "active_match_groups": [
                group.to_dict()
                for group in sorted(
                    active_match_groups,
                    key=lambda item: (item.match_id, item.match_snapshot_id),
                )
            ],
            "inactive_current_match_snapshot_ids": sorted(inactive_current_match_snapshot_ids),
        },
    )


def build_learning_dataset_partition_request_fingerprint_v1(
    *,
    mode: str,
    algorithm: str,
    base_random_seed: int,
    partition_weights: LearningDatasetPartitionWeightsV1,
    learning_dataset: LearningDatasetV2,
    player_catalog: LearningCorpusPlayerCatalogV1,
) -> str:
    """Fingerprints every exact preparation Request field except itself."""
    return _identifier(
        LEARNING_DATASET_PARTITION_REQUEST_DOMAIN,
        {
            "learning_dataset_partition_preparation_version": (
                LEARNING_DATASET_PARTITION_PREPARATION_VERSION
            ),
            "mode": mode,
            "algorithm": algorithm,
            "base_random_seed": base_random_seed,
            "partition_weights": partition_weights.to_dict(),
            "learning_dataset": learning_dataset.to_dict(),
            "player_catalog": player_catalog.to_dict(),
        },
    )


def validate_learning_dataset_partition_request_fingerprint_v1(
    request: LearningDatasetPartitionPreparationRequestV1,
) -> None:
    expected = build_learning_dataset_partition_request_fingerprint_v1(
        mode=request.mode,
        algorithm=request.algorithm,
        base_random_seed=request.base_random_seed,
        partition_weights=request.partition_weights,
        learning_dataset=request.learning_dataset,
        player_catalog=request.player_catalog,
    )
    if request.request_fingerprint != expected:
        raise ValueError("request_fingerprint must cover the exact preparation Request.")


def derive_learning_dataset_partition_seed_v1(
    mode: str,
    base_random_seed: int,
    source_identity_fingerprint: str,
) -> int:
    """Derives one process-stable mode-specific partition seed."""
    if mode not in _SEED_DOMAIN_BY_MODE:
        raise ValueError("mode must be known_player or unseen_player.")
    if type(base_random_seed) is not int:
        raise ValueError("base_random_seed must be an integer and not a boolean.")
    _require_hash(source_identity_fingerprint, "source_identity_fingerprint")
    material = (
        f"skat-ai\0{_SEED_DOMAIN_BY_MODE[mode]}\0{base_random_seed}\0"
        f"{source_identity_fingerprint}\0partition"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def derive_learning_dataset_partition_tie_break_key_v1(
    partition_seed: int,
    stable_item_identity: str,
) -> int:
    """Derives one deterministic key consulted only after objective equality."""
    if type(partition_seed) is not int or partition_seed < 0:
        raise ValueError("partition_seed must be a non-negative integer.")
    _require_identifier(stable_item_identity, "stable_item_identity")
    material = (
        f"skat-ai\0learning_dataset_v2_partition_tie_v1\0{partition_seed}\0{stable_item_identity}"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _normalized_audit_dict(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    normalized.pop("audit_fingerprint", None)
    # The containing Plan reference is recursive and cannot participate in either hash.
    normalized["plan_fingerprint"] = None
    return normalized


def build_learning_dataset_partition_audit_fingerprint_v1(
    audit: LearningDatasetPartitionLeakageAuditV1 | dict[str, Any],
) -> str:
    material = (
        audit.to_dict() if isinstance(audit, LearningDatasetPartitionLeakageAuditV1) else audit
    )
    return _identifier(
        LEARNING_DATASET_PARTITION_AUDIT_FINGERPRINT_DOMAIN,
        _normalized_audit_dict(material),
    )


def _normalized_plan_dict(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    normalized.pop("plan_fingerprint", None)
    leakage_audit = normalized.get("leakage_audit")
    if leakage_audit is not None:
        normalized["leakage_audit"] = {
            **leakage_audit,
            "plan_fingerprint": None,
        }
    return normalized


def build_learning_dataset_partition_plan_fingerprint_v1(
    plan: LearningDatasetPartitionPlanV1 | dict[str, Any],
) -> str:
    material = plan.to_dict() if isinstance(plan, LearningDatasetPartitionPlanV1) else plan
    return _identifier(
        LEARNING_DATASET_PARTITION_PLAN_FINGERPRINT_DOMAIN,
        _normalized_plan_dict(material),
    )


def build_learning_dataset_partitioned_view_fingerprint_v1(
    view: LearningDatasetPartitionedViewV1 | dict[str, Any],
) -> str:
    material = view.to_dict() if isinstance(view, LearningDatasetPartitionedViewV1) else view
    material = dict(material)
    material.pop("partitioned_view_fingerprint", None)
    return _identifier(
        LEARNING_DATASET_PARTITIONED_VIEW_FINGERPRINT_DOMAIN,
        material,
    )


def build_learning_dataset_partition_export_id_v1(material: dict[str, Any]) -> str:
    """Builds the export ID from every export field except itself."""
    identity_material = dict(material)
    identity_material.pop("export_id", None)
    return _identifier(LEARNING_DATASET_PARTITION_EXPORT_ID_DOMAIN, identity_material)


def component_fingerprint_material_v1(
    component: LearningDatasetPlayerComponentV1,
) -> dict[str, Any]:
    """Returns the narrow component identity material for focused verification."""
    return {
        "learning_dataset_player_component_version": (
            component.learning_dataset_player_component_version
        ),
        "match_snapshot_ids": list(component.match_snapshot_ids),
        "player_ids": list(component.player_ids),
    }
