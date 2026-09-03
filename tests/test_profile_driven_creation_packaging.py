from __future__ import annotations

import importlib
import importlib.resources
from pathlib import Path

import skatmind

ROOT = Path(__file__).resolve().parents[1]

_PROFILE_DRIVEN_MODULES = (
    "friendly_creation_rendering",
    "frontend_identifier_generation",
    "profile_driven_creation",
    "profile_player_contracts",
    "profile_player_operations",
    "profile_settings_rendering",
)


def test_profile_driven_creation_modules_are_private_package_modules() -> None:
    for name in _PROFILE_DRIVEN_MODULES:
        module = importlib.import_module(f"skatmind.app_web.{name}")
        assert module.__name__ == f"skatmind.app_web.{name}"
        assert (ROOT / "src" / "skatmind" / "app_web" / f"{name}.py").is_file()

    assert "PROFILE_DRIVEN_FORM_DEFAULTS_VERSION" not in skatmind.__all__


def test_profile_driven_creation_uses_packaged_local_resources_only() -> None:
    resources = importlib.resources.files("skatmind.app_web")
    css = resources.joinpath("assets/app.css").read_bytes()
    english = resources.joinpath("locales/en.json").read_bytes()
    german = resources.joinpath("locales/de.json").read_bytes()

    for selector in (
        b".friendly-create",
        b".managed-item-grid",
        b".local-settings",
        b".known-player-grid",
    ):
        assert selector in css
    assert b'"settings.players.heading"' in english
    assert b'"settings.players.heading"' in german
    assert b"http://" not in css and b"https://" not in css
