import hashlib

import pytest
from test_historical_game import build_historical_input
from test_training_dataset_preparation import build_preparation_input

from skatmind.dataset_preparation_identity import (
    DATASET_KNOWN_OPPONENT_SEED_DOMAIN,
    DATASET_UNSEEN_PLAYER_SEED_DOMAIN,
    build_source_content_fingerprint,
    build_source_identity_fingerprint,
    derive_dataset_partition_seed,
    derive_dataset_partition_tie_break_key,
)
from skatmind.training_dataset_preparation import (
    build_training_dataset_preparation_request,
)


def test_fingerprints_are_lowercase_sha256_and_source_order_independent() -> None:
    data = build_preparation_input(
        [build_historical_input(), build_historical_input(game_type="null")]
    )
    request = build_training_dataset_preparation_request(data)
    reordered = build_training_dataset_preparation_request(
        {**data, "records": list(reversed(data["records"]))}
    )

    identity = build_source_identity_fingerprint(request)
    content = build_source_content_fingerprint(request)

    assert len(identity) == len(content) == 64
    assert all(character in "0123456789abcdef" for character in identity + content)
    assert build_source_identity_fingerprint(reordered) == identity
    assert build_source_content_fingerprint(reordered) == content


def test_identity_excludes_labels_notes_cards_and_declaration_content() -> None:
    grand = build_preparation_input([build_historical_input(game_type="grand")])
    grand["records"][0]["historical_game"]["played_at"] = "2026-01-01T00:00:00Z"
    changed = build_preparation_input([build_historical_input(game_type="null")])
    changed["records"][0]["historical_game"]["played_at"] = "2026-01-01T00:00:00Z"
    changed["records"][0]["historical_game"]["players"][0][
        "player_label"
    ] = "Changed label"
    changed["records"][0]["provenance"]["notes"] = "Changed note"
    first = build_training_dataset_preparation_request(grand)
    second = build_training_dataset_preparation_request(changed)

    assert build_source_identity_fingerprint(first) == (
        build_source_identity_fingerprint(second)
    )
    assert build_source_content_fingerprint(first) != (
        build_source_content_fingerprint(second)
    )


def test_identity_fingerprint_changes_for_split_relevant_source_facts() -> None:
    data = build_preparation_input()
    baseline = build_training_dataset_preparation_request(data)
    changed = build_preparation_input()
    changed["records"][0]["historical_game"]["played_at"] = (
        "2026-01-02T00:00:00Z"
    )

    assert build_source_identity_fingerprint(baseline) != (
        build_source_identity_fingerprint(
            build_training_dataset_preparation_request(changed)
        )
    )


@pytest.mark.parametrize(
    ("mode", "domain"),
    [
        ("known_opponent", DATASET_KNOWN_OPPONENT_SEED_DOMAIN),
        ("unseen_player", DATASET_UNSEEN_PLAYER_SEED_DOMAIN),
    ],
)
def test_partition_seed_and_tie_key_match_independent_sha256_oracle(
    mode: str,
    domain: str,
) -> None:
    source_fingerprint = "ab" * 32
    base_seed = 73
    expected_seed_material = (
        f"skat-ai\0{base_seed}\0{domain}\0{source_fingerprint}\0partition"
    ).encode()
    expected_key_material = (
        f"skat-ai\0{base_seed}\0{domain}\0{source_fingerprint}"
        "\0item\0record-17"
    ).encode()

    assert derive_dataset_partition_seed(
        mode, base_seed, source_fingerprint
    ) == int.from_bytes(hashlib.sha256(expected_seed_material).digest()[:8], "big")
    assert derive_dataset_partition_tie_break_key(
        mode,
        base_seed,
        source_fingerprint,
        "record-17",
    ) == int.from_bytes(hashlib.sha256(expected_key_material).digest()[:8], "big")


def test_seed_helpers_are_mode_separated_stable_and_strict() -> None:
    fingerprint = "01" * 32
    known = derive_dataset_partition_seed("known_opponent", 1, fingerprint)
    unseen = derive_dataset_partition_seed("unseen_player", 1, fingerprint)

    assert known != unseen
    assert known == derive_dataset_partition_seed("known_opponent", 1, fingerprint)
    assert derive_dataset_partition_tie_break_key(
        "known_opponent", 1, fingerprint, "A"
    ) != derive_dataset_partition_tie_break_key(
        "known_opponent", 1, fingerprint, "B"
    )
    with pytest.raises(ValueError, match="must not be a boolean"):
        derive_dataset_partition_seed("known_opponent", True, fingerprint)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        derive_dataset_partition_seed("known_opponent", 1, "ABC")
    with pytest.raises(ValueError, match="non-empty, non-padded"):
        derive_dataset_partition_tie_break_key(
            "known_opponent", 1, fingerprint, " padded"
        )
