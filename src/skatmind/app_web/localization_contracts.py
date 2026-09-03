from __future__ import annotations

from dataclasses import dataclass

BILINGUAL_FRONTEND_CONTRACT_VERSION = 1
FRONTEND_TRANSLATION_CATALOG_VERSION = 1

BILINGUAL_FRONTEND_POLICIES = (
    "technical_contracts_and_machine_values_remain_english",
    "unified_frontend_visible_content_supports_german_and_english",
    "one_private_local_frontend_profile_per_managed_data_root",
    "saved_language_overrides_browser_language",
    "browser_language_bootstraps_only_without_saved_preference",
    "user_facing_names_replace_required_manual_internal_ids",
    "normal_workflows_are_task_first_and_profile_driven",
    "advanced_settings_are_secondary_explicit_and_explained",
    "validation_preserves_safe_values_and_workflow_context",
    "home_separates_record_analyze_learn_and_product_information",
    "language_and_profile_never_change_product_semantics",
    "no_external_translation_profile_sync_or_cloud_service",
)

IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES = (
    "technical_contracts_and_machine_values_remain_english",
    "unified_frontend_visible_content_supports_german_and_english",
    "one_private_local_frontend_profile_per_managed_data_root",
    "saved_language_overrides_browser_language",
    "browser_language_bootstraps_only_without_saved_preference",
    "user_facing_names_replace_required_manual_internal_ids",
    "validation_preserves_safe_values_and_workflow_context",
    "home_separates_record_analyze_learn_and_product_information",
    "language_and_profile_never_change_product_semantics",
    "no_external_translation_profile_sync_or_cloud_service",
)

SUPPORTED_FRONTEND_LOCALES = ("de", "en")
FRONTEND_REFERENCE_LOCALE = "en"
FRONTEND_FALLBACK_LOCALE = "en"
FRONTEND_LOCALE_RESOLUTION_SOURCES = ("saved_profile", "browser", "fallback")


def _require_canonical_value(value: object, values: tuple[str, ...], name: str) -> None:
    if type(value) is not str or value not in values:
        raise ValueError(f"{name} must be one canonical value.")


@dataclass(frozen=True, slots=True)
class FrontendLocaleResolutionV1:
    locale: str
    source: str

    def __post_init__(self) -> None:
        _require_canonical_value(self.locale, SUPPORTED_FRONTEND_LOCALES, "locale")
        _require_canonical_value(
            self.source,
            FRONTEND_LOCALE_RESOLUTION_SOURCES,
            "source",
        )


@dataclass(frozen=True, slots=True)
class BrowserSafeFrontendProfileStateV1:
    locale: str
    resolution_source: str
    profile_status: str
    profile_revision: int | None
    profile_generation: int
    warning: bool

    def __post_init__(self) -> None:
        _require_canonical_value(self.locale, SUPPORTED_FRONTEND_LOCALES, "locale")
        _require_canonical_value(
            self.resolution_source,
            FRONTEND_LOCALE_RESOLUTION_SOURCES,
            "resolution_source",
        )
        _require_canonical_value(
            self.profile_status,
            ("absent", "available", "invalid"),
            "profile_status",
        )
        if self.profile_revision is not None and (
            type(self.profile_revision) is not int or self.profile_revision < 0
        ):
            raise ValueError("profile_revision must be null or a non-negative integer.")
        if type(self.profile_generation) is not int or self.profile_generation < 0:
            raise ValueError("profile_generation must be a non-negative integer.")
        if type(self.warning) is not bool:
            raise ValueError("warning must be a boolean.")
        if self.warning != (self.profile_status == "invalid"):
            raise ValueError("warning must identify exactly an invalid profile.")
        if self.profile_status == "available":
            if self.profile_revision is None:
                raise ValueError("Available profile state requires one revision.")
        elif self.profile_revision is not None:
            raise ValueError("Only available profile state may expose a revision.")
        if self.resolution_source == "saved_profile" and self.profile_status != "available":
            raise ValueError("Saved-profile resolution requires an available profile.")
        if self.profile_status == "invalid" and (
            self.locale != FRONTEND_FALLBACK_LOCALE or self.resolution_source != "fallback"
        ):
            raise ValueError("Invalid profile state must use the English fallback.")


def validate_bilingual_frontend_contract_v1() -> None:
    if len(BILINGUAL_FRONTEND_POLICIES) != len(set(BILINGUAL_FRONTEND_POLICIES)):
        raise ValueError("Bilingual frontend policies must not repeat.")
    if not set(IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES).issubset(BILINGUAL_FRONTEND_POLICIES):
        raise ValueError("Implemented policies must belong to the frozen vocabulary.")
    if SUPPORTED_FRONTEND_LOCALES != ("de", "en"):
        raise ValueError("Supported frontend locales must remain canonical.")
    if FRONTEND_REFERENCE_LOCALE != "en" or FRONTEND_FALLBACK_LOCALE != "en":
        raise ValueError("Reference and fallback locale must remain English.")
