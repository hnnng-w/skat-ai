"""Internal canonical identity and reviewed migration boundary for the SkatMind rename."""

SKATMIND_RENAME_CONTRACT_VERSION = 1

SKATMIND_PRODUCT_DISPLAY_NAME = "SkatMind"
SKATMIND_REPOSITORY_SLUG = "hnnng-w/skatmind"
SKATMIND_DISTRIBUTION_NAME = "skatmind"
SKATMIND_IMPORT_NAMESPACE = "skatmind"
SKATMIND_CLI_COMMAND = "skatmind"
SKATMIND_SCHEMA_BASE_URI = "https://example.local/skatmind/"
SKATMIND_DEFAULT_MEMORY_INPUT_REFERENCE = "memory://skatmind/request"
SKATMIND_DOCUMENT_KIND_PREFIX = "skatmind_"
SKATMIND_SHA256_DOMAIN_PREFIX = b"skatmind\0"

SKATMIND_RENAME_POLICIES = (
    "single_canonical_skatmind_active_identity",
    "no_active_skat_ai_import_or_cli_alias",
    "legacy_persisted_identities_are_strict_input_only",
    "new_writes_use_skatmind_identifiers",
    "legacy_content_addressed_objects_keep_verified_opaque_ids",
    "historical_release_evidence_is_not_rewritten",
    "repository_rename_is_manual_after_merge",
)

# These pre-rename salts are historical deterministic protocol evidence, not emitted IDs.
SKATMIND_FROZEN_DETERMINISTIC_SEED_PROTOCOLS = (
    "skatmind.coherent_hidden_world.derive_simulation_child_seed",
    "skatmind.dataset_preparation_identity.derive_dataset_partition_seed",
    "skatmind.dataset_preparation_identity.derive_dataset_partition_tie_break_key",
    (
        "skatmind.historical_information_set_search_review."
        "derive_historical_information_set_search_decision_seed"
    ),
    "skatmind.historical_search_review.derive_historical_search_decision_seed",
    (
        "skatmind.learning_dataset_v2_partition_identity."
        "derive_learning_dataset_partition_seed_v1"
    ),
    (
        "skatmind.learning_dataset_v2_partition_identity."
        "derive_learning_dataset_partition_tie_break_key_v1"
    ),
)

SKATMIND_LEGACY_PERSISTED_DOCUMENT_KINDS = (
    "skat_ai_session",
    "skat_ai_match_workspace",
    "skat_ai_learning_corpus_catalog",
    "skat_ai_match_analysis_report_source",
)

SKATMIND_RENAME_INVENTORY_CLASSIFICATIONS = (
    "active_identity",
    "legacy_persisted_input",
    "historical_evidence",
    "external_or_legal_text",
)
