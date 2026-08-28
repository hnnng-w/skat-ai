import hashlib
import json
from typing import Any

from skatmind.dataset_partition_policy import DATASET_PARTITION_POLICY_MODES
from skatmind.historical_game import build_serializable_historical_record
from skatmind.training_dataset import build_serializable_training_provenance

DATASET_KNOWN_OPPONENT_SEED_DOMAIN = "dataset_known_opponent_split_v1"
DATASET_UNSEEN_PLAYER_SEED_DOMAIN = "dataset_unseen_player_split_v1"

_SEED_DOMAINS = {
    "known_opponent": DATASET_KNOWN_OPPONENT_SEED_DOMAIN,
    "unseen_player": DATASET_UNSEEN_PLAYER_SEED_DOMAIN,
}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _canonical_source_identity_record(record: Any) -> dict[str, Any]:
    provenance = record.provenance
    return {
        "record_id": record.record_id,
        "historical_game_id": record.historical_game.game_id,
        "source_identity": (
            {
                "source_type": provenance.source_type,
                "source_name": provenance.source_name,
                "source_record_id": provenance.source_record_id,
            }
            if provenance.source_record_id is not None
            else None
        ),
        "played_at": record.historical_game.played_at,
        "player_ids": sorted(player.player_id for player in record.historical_game.players),
    }


def build_source_identity_fingerprint(request: Any) -> str:
    """Fingerprints only stable split-relevant request and source identities."""
    records = sorted(
        (_canonical_source_identity_record(record) for record in request.records),
        key=lambda value: _canonical_json_bytes(value),
    )
    return _sha256_fingerprint(
        {
            "preparation_version": request.preparation_version,
            "dataset_id": request.dataset_id,
            "dataset_version": request.dataset_version,
            "feature_generation_version": request.feature_generation_version,
            "target": request.target,
            "mode": request.mode,
            "records": records,
        }
    )


def build_source_content_fingerprint(request: Any) -> str:
    """Fingerprints exact canonical source content independently of source order."""
    records = sorted(
        (
            {
                "record_id": record.record_id,
                "provenance": build_serializable_training_provenance(record.provenance),
                "historical_game": build_serializable_historical_record(record.historical_game),
            }
            for record in request.records
        ),
        key=lambda value: _canonical_json_bytes(value),
    )
    return _sha256_fingerprint(
        {
            "preparation_version": request.preparation_version,
            "dataset_id": request.dataset_id,
            "dataset_version": request.dataset_version,
            "feature_generation_version": request.feature_generation_version,
            "target": request.target,
            "mode": request.mode,
            "records": records,
        }
    )


def build_unseen_player_selection_fingerprint(
    request: Any,
    source_facts: tuple[Any, ...],
) -> str:
    """Fingerprints only identities allowed to select an unseen-player split."""
    player_ids_by_record = sorted(
        (
            {
                "record_id": fact.record_id,
                "player_ids": sorted(fact.player_ids),
            }
            for fact in source_facts
        ),
        key=lambda value: value["record_id"],
    )
    return _sha256_fingerprint(
        {
            "preparation_version": request.preparation_version,
            "dataset_id": request.dataset_id,
            "dataset_version": request.dataset_version,
            "algorithm": "component_balanced_unseen_player_v1",
            "record_ids": sorted(fact.record_id for fact in source_facts),
            "historical_game_ids": sorted(fact.historical_game_id for fact in source_facts),
            "player_ids_by_record": player_ids_by_record,
        }
    )


def _validate_seed_inputs(
    mode: str,
    base_random_seed: int,
    source_identity_fingerprint: str,
) -> str:
    if mode not in DATASET_PARTITION_POLICY_MODES:
        raise ValueError(f"mode must be one of {list(DATASET_PARTITION_POLICY_MODES)}.")
    if isinstance(base_random_seed, bool) or not isinstance(base_random_seed, int):
        raise ValueError("base_random_seed must be an integer and must not be a boolean.")
    if (
        not isinstance(source_identity_fingerprint, str)
        or len(source_identity_fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in source_identity_fingerprint)
    ):
        raise ValueError(
            "source_identity_fingerprint must be a lowercase SHA-256 hexadecimal value."
        )
    return _SEED_DOMAINS[mode]


def derive_dataset_partition_seed(
    mode: str,
    base_random_seed: int,
    source_identity_fingerprint: str,
) -> int:
    """Derives one process-stable mode-specific partition seed."""
    domain = _validate_seed_inputs(mode, base_random_seed, source_identity_fingerprint)
    material = (
        f"skat-ai\0{base_random_seed}\0{domain}\0{source_identity_fingerprint}\0partition"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def derive_dataset_partition_tie_break_key(
    mode: str,
    base_random_seed: int,
    source_identity_fingerprint: str,
    stable_item_identity: str,
) -> int:
    """Derives one stable-item key without source order or private game data."""
    domain = _validate_seed_inputs(mode, base_random_seed, source_identity_fingerprint)
    if (
        not isinstance(stable_item_identity, str)
        or not stable_item_identity
        or stable_item_identity != stable_item_identity.strip()
    ):
        raise ValueError("stable_item_identity must be a non-empty, non-padded string.")
    material = (
        f"skat-ai\0{base_random_seed}\0{domain}\0"
        f"{source_identity_fingerprint}\0item\0{stable_item_identity}"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
