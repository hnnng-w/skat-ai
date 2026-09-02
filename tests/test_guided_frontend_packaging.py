from __future__ import annotations

import importlib
import importlib.resources
from pathlib import Path

import skatmind

ROOT = Path(__file__).resolve().parents[1]

_GUIDED_MODULES = (
    "card_form",
    "execution",
    "form_parsing",
    "form_registry",
    "form_state",
    "guided_contracts",
    "guided_rendering",
    "historical_form",
    "historical_form_parsing",
    "information_architecture",
    "json_transfer",
    "position_form",
    "result_presentation",
    "result_rendering",
    "workflow_operations",
    "workflow_state",
    "validation_contracts",
    "validation_mapping",
    "validation_rendering",
)


def test_guided_frontend_modules_are_private_package_discovered_modules() -> None:
    for name in _GUIDED_MODULES:
        module = importlib.import_module(f"skatmind.app_web.{name}")
        assert module.__name__ == f"skatmind.app_web.{name}"
        assert (ROOT / "src" / "skatmind" / "app_web" / f"{name}.py").is_file()

    public_names = set(skatmind.__all__)
    assert not public_names.intersection(
        {
            "GUIDED_ANALYSIS_FRONTEND_VERSION",
            "GUIDED_POSITION_FORM_VERSION",
            "GUIDED_HISTORICAL_REVIEW_FORM_VERSION",
            "FRONTEND_RESULT_PRESENTATION_VERSION",
            "FRONTEND_JSON_TRANSFER_VERSION",
            "PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION",
            "FRONTEND_INFORMATION_ARCHITECTURE_VERSION",
            "FRONTEND_VALIDATION_PRESERVATION_VERSION",
        }
    )


def test_existing_local_app_resources_contain_guided_no_javascript_styles() -> None:
    resources = importlib.resources.files("skatmind.app_web")
    css = resources.joinpath("assets/app.css")
    template = resources.joinpath("templates/app.html")

    assert css.is_file() and template.is_file()
    css_bytes = css.read_bytes()
    combined = css_bytes + template.read_bytes()
    for required in (
        b".home-group",
        b".scope-guide",
        b".task-disclosure",
        b".workflow-form",
        b".card-grid",
        b".error-summary",
        b".field-error",
        b'[aria-invalid="true"]',
        b".result-presentation",
    ):
        assert required in css_bytes
    assert b"<script" not in combined
    assert b"http://" not in combined and b"https://" not in combined
