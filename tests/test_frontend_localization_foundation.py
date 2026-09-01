from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from string import Formatter

import pytest

import skatmind
import skatmind.api.v1 as public_api
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.locale_resolution import (
    parse_accept_language_v1,
    resolve_frontend_locale_v1,
)
from skatmind.app_web.localization_contracts import (
    BILINGUAL_FRONTEND_CONTRACT_VERSION,
    BILINGUAL_FRONTEND_POLICIES,
    FRONTEND_FALLBACK_LOCALE,
    FRONTEND_REFERENCE_LOCALE,
    FRONTEND_TRANSLATION_CATALOG_VERSION,
    IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES,
    SUPPORTED_FRONTEND_LOCALES,
    BrowserSafeFrontendProfileStateV1,
    FrontendLocaleResolutionV1,
    validate_bilingual_frontend_contract_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.rendering import render_app_content_page_v1
from skatmind.app_web.translation_catalog import (
    load_frontend_translation_catalogs_v1,
    translate_frontend_message_v1,
)


def test_versions_policy_vocabulary_and_implemented_subset_are_exact() -> None:
    assert BILINGUAL_FRONTEND_CONTRACT_VERSION == 1
    assert FRONTEND_TRANSLATION_CATALOG_VERSION == 1
    assert BILINGUAL_FRONTEND_POLICIES == (
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
    assert IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES == (
        "technical_contracts_and_machine_values_remain_english",
        "unified_frontend_visible_content_supports_german_and_english",
        "one_private_local_frontend_profile_per_managed_data_root",
        "saved_language_overrides_browser_language",
        "browser_language_bootstraps_only_without_saved_preference",
        "language_and_profile_never_change_product_semantics",
        "no_external_translation_profile_sync_or_cloud_service",
    )
    validate_bilingual_frontend_contract_v1()


def test_localization_and_profile_contracts_are_not_public_exports() -> None:
    for name in (
        "BILINGUAL_FRONTEND_CONTRACT_VERSION",
        "FRONTEND_TRANSLATION_CATALOG_VERSION",
        "LOCAL_FRONTEND_PROFILE_VERSION",
        "LocalFrontendProfileV1",
    ):
        assert name not in skatmind.__all__
        assert not hasattr(skatmind, name)
        assert name not in public_api.__all__
        assert not hasattr(public_api, name)


def test_locale_contracts_and_browser_safe_values_are_exact() -> None:
    assert SUPPORTED_FRONTEND_LOCALES == ("de", "en")
    assert FRONTEND_REFERENCE_LOCALE == "en"
    assert FRONTEND_FALLBACK_LOCALE == "en"
    assert FrontendLocaleResolutionV1("de", "browser").locale == "de"
    with pytest.raises(ValueError):
        FrontendLocaleResolutionV1("fr", "browser")
    with pytest.raises(ValueError):
        BrowserSafeFrontendProfileStateV1(
            locale="en",
            resolution_source="fallback",
            profile_status="absent",
            profile_revision=True,  # type: ignore[arg-type]
            profile_generation=0,
            warning=False,
        )
    with pytest.raises(ValueError):
        BrowserSafeFrontendProfileStateV1(
            locale="de",
            resolution_source="browser",
            profile_status="invalid",
            profile_revision=None,
            profile_generation=0,
            warning=True,
        )


def _placeholder_names(message: str) -> frozenset[str]:
    return frozenset(
        name
        for _literal, name, _format_spec, _conversion in Formatter().parse(message)
        if name is not None
    )


def test_catalog_resources_are_strict_ordered_and_have_exact_parity() -> None:
    catalogs = load_frontend_translation_catalogs_v1()
    assert tuple(catalogs) == ("de", "en")
    assert tuple(catalogs["de"]) == tuple(catalogs["en"])
    assert tuple(catalogs["en"]) == tuple(sorted(catalogs["en"]))
    assert len(catalogs["en"]) == 145
    for locale in SUPPORTED_FRONTEND_LOCALES:
        raw = files("skatmind.app_web").joinpath(f"locales/{locale}.json").read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        document = json.loads(raw.decode("utf-8"))
        assert type(document) is dict
        assert all(type(value) is str and value.strip() for value in document.values())
    for key in catalogs["en"]:
        assert _placeholder_names(catalogs["de"][key]) == _placeholder_names(
            catalogs["en"][key]
        )


def test_translation_lookup_is_strict_plain_text_without_locale_fallback() -> None:
    assert translate_frontend_message_v1("en", "navigation.home") == "Home"
    assert translate_frontend_message_v1("de", "navigation.home") == "Startseite"
    assert translate_frontend_message_v1(
        "de",
        "about.installation.package_value",
        version="0.17.0",
    ) == "Paket 0.17.0"
    assert translate_frontend_message_v1(
        "en",
        "about.installation.package_value",
        version="<unsafe>",
    ) == "Package <unsafe>"
    with pytest.raises(KeyError):
        translate_frontend_message_v1("de", "missing.production.key")
    with pytest.raises(ValueError):
        translate_frontend_message_v1(
            "de",
            "about.installation.package_value",
        )
    with pytest.raises(ValueError):
        translate_frontend_message_v1("fr", "navigation.home")


@pytest.mark.parametrize(
    ("header", "expected"),
    (
        ("de", "de"),
        ("de-DE", "de"),
        ("en", "en"),
        ("en-US", "en"),
        ("en;q=0.4,de-DE;q=0.8", "de"),
        ("de;q=0.8,en;q=0.8", "de"),
        ("en;q=0.8,de;q=0.8", "en"),
        ("fr,de;q=0.7", "de"),
        ("de;q=0,en;q=0.5", "en"),
        ("*", None),
        ("fr-FR", None),
        ("de;q=wat", None),
        ("de;q=1.5", None),
        ("de;q=0.1;q=0.9,en;q=0.8", "en"),
        ("", None),
    ),
)
def test_accept_language_parsing_is_deterministic(header: str, expected: str | None) -> None:
    assert parse_accept_language_v1(header) == expected


def test_locale_resolution_precedence_and_invalid_profile_fallback() -> None:
    saved = resolve_frontend_locale_v1(
        saved_language="en",
        accept_language="de-DE",
        profile_status="available",
    )
    assert saved == FrontendLocaleResolutionV1("en", "saved_profile")
    browser = resolve_frontend_locale_v1(
        saved_language=None,
        accept_language="de-DE",
        profile_status="absent",
    )
    assert browser == FrontendLocaleResolutionV1("de", "browser")
    invalid = resolve_frontend_locale_v1(
        saved_language=None,
        accept_language="de-DE",
        profile_status="invalid",
    )
    assert invalid == FrontendLocaleResolutionV1("en", "fallback")
    unsupported = resolve_frontend_locale_v1(
        saved_language=None,
        accept_language="fr-FR",
        profile_status="available",
    )
    assert unsupported == FrontendLocaleResolutionV1("en", "fallback")


def test_shell_substitution_does_not_reinterpret_content_as_template_markup(
    tmp_path: Path,
) -> None:
    context = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    rendered = render_app_content_page_v1(
        context.browser_state,
        "/sessions",
        title="Marker test",
        content="<p>{{FOOTER}}</p>",
    )
    assert "<p>{{FOOTER}}</p>" in rendered
    assert rendered.count("Local Skat analysis. No cloud service.") == 1
