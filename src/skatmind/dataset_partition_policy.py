from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

DATASET_PARTITION_POLICY_VERSION = 1
DATASET_PARTITION_POLICY_MODES = ("known_opponent", "unseen_player")
DATASET_PARTITION_AUDIT_MODES = (
    "report_only",
    "known_opponent",
    "unseen_player",
)
CANONICAL_DATASET_PARTITIONS = ("train", "validation", "test")

DatasetPartitionPolicyMode = Literal["known_opponent", "unseen_player"]
DatasetPartitionAuditMode = Literal[
    "report_only",
    "known_opponent",
    "unseen_player",
]


@dataclass(frozen=True)
class DatasetPartitionPolicy:
    """One explicit version-1 training-dataset partition contract."""

    policy_version: int
    mode: DatasetPartitionPolicyMode


@dataclass(frozen=True)
class PlayerPartitionMembership:
    """Ordered partition membership for one exact stable player identity."""

    player_id: str
    player_label: str | None
    partitions: tuple[str, ...]
    record_ids_by_partition: dict[str, tuple[str, ...]]
    game_ids_by_partition: dict[str, tuple[str, ...]]
    first_appearance_index: int


@dataclass
class _MembershipAccumulator:
    player_id: str
    first_appearance_index: int
    labels: list[str] = field(default_factory=list)
    record_ids_by_partition: dict[str, list[str]] = field(
        default_factory=lambda: {
            partition: [] for partition in CANONICAL_DATASET_PARTITIONS
        }
    )
    game_ids_by_partition: dict[str, list[str]] = field(
        default_factory=lambda: {
            partition: [] for partition in CANONICAL_DATASET_PARTITIONS
        }
    )


def build_dataset_partition_policy(value: Any) -> DatasetPartitionPolicy:
    """Builds one strict version-1 partition policy object."""
    if not isinstance(value, dict):
        raise ValueError("training_dataset_input.partition_policy must be an object.")
    required_fields = {"policy_version", "mode"}
    missing_fields = sorted(required_fields - value.keys())
    if missing_fields:
        raise ValueError(
            "training_dataset_input.partition_policy is missing required fields: "
            f"{missing_fields}."
        )
    unexpected_fields = sorted(value.keys() - required_fields)
    if unexpected_fields:
        raise ValueError(
            "training_dataset_input.partition_policy has unsupported fields: "
            f"{unexpected_fields}."
        )
    policy_version = value["policy_version"]
    if (
        isinstance(policy_version, bool)
        or not isinstance(policy_version, int)
        or policy_version != DATASET_PARTITION_POLICY_VERSION
    ):
        raise ValueError(
            "training_dataset_input.partition_policy.policy_version must currently "
            f"equal {DATASET_PARTITION_POLICY_VERSION}."
        )
    mode = value["mode"]
    if mode not in DATASET_PARTITION_POLICY_MODES:
        raise ValueError(
            "training_dataset_input.partition_policy.mode must be one of "
            f"{list(DATASET_PARTITION_POLICY_MODES)}."
        )
    return DatasetPartitionPolicy(policy_version=policy_version, mode=mode)


def build_serializable_dataset_partition_policy(
    policy: DatasetPartitionPolicy,
) -> dict[str, Any]:
    """Builds the canonical public partition-policy representation."""
    return {
        "policy_version": policy.policy_version,
        "mode": policy.mode,
    }


def collect_player_partition_memberships(
    records: Iterable[Any],
) -> tuple[PlayerPartitionMembership, ...]:
    """Collects exact player membership in canonical dataset record order."""
    accumulators: dict[str, _MembershipAccumulator] = {}
    for record_index, record in enumerate(records):
        partition = record.partition
        game = record.historical_game
        for player in game.players:
            accumulator = accumulators.get(player.player_id)
            if accumulator is None:
                accumulator = _MembershipAccumulator(
                    player_id=player.player_id,
                    first_appearance_index=record_index,
                )
                accumulators[player.player_id] = accumulator
            if player.player_label is not None and player.player_label not in accumulator.labels:
                accumulator.labels.append(player.player_label)
            accumulator.record_ids_by_partition[partition].append(record.record_id)
            accumulator.game_ids_by_partition[partition].append(game.game_id)

    memberships = []
    for accumulator in accumulators.values():
        partitions = tuple(
            partition
            for partition in CANONICAL_DATASET_PARTITIONS
            if accumulator.game_ids_by_partition[partition]
        )
        memberships.append(
            PlayerPartitionMembership(
                player_id=accumulator.player_id,
                player_label=(
                    accumulator.labels[0] if len(accumulator.labels) == 1 else None
                ),
                partitions=partitions,
                record_ids_by_partition={
                    partition: tuple(accumulator.record_ids_by_partition[partition])
                    for partition in CANONICAL_DATASET_PARTITIONS
                },
                game_ids_by_partition={
                    partition: tuple(accumulator.game_ids_by_partition[partition])
                    for partition in CANONICAL_DATASET_PARTITIONS
                },
                first_appearance_index=accumulator.first_appearance_index,
            )
        )
    return tuple(memberships)


def get_cross_partition_player_memberships(
    records: Iterable[Any],
) -> tuple[PlayerPartitionMembership, ...]:
    """Returns every exact player identity occurring in multiple partitions."""
    return tuple(
        membership
        for membership in collect_player_partition_memberships(records)
        if len(membership.partitions) > 1
    )


def format_unseen_player_policy_violation(
    violations: tuple[PlayerPartitionMembership, ...],
) -> str:
    """Formats all unseen-player conflicts in deterministic public order."""
    details = "; ".join(
        f"'{membership.player_id}' in {list(membership.partitions)}"
        for membership in violations
    )
    return (
        "Declared unseen_player partition policy requires every stable player to "
        "occur in exactly one partition. Conflicting players: "
        f"{details}."
    )
