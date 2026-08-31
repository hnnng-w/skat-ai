from __future__ import annotations

from html import escape
from importlib.resources import files
from pathlib import Path

from .contracts import APP_ROUTE_PATHS, BrowserSafeApplicationStateV1
from .guided_rendering import render_analyze_workflow_v1, render_review_workflow_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1


def _template() -> str:
    return (
        files("skatmind.app_web")
        .joinpath("templates/app.html")
        .read_text(encoding="utf-8")
    )


def _navigation(state: BrowserSafeApplicationStateV1, current_route: str) -> str:
    items = []
    for item in state.navigation:
        current = ' aria-current="page"' if item.route == current_route else ""
        items.append(
            f'<li><a href="{escape(item.route, quote=True)}"{current}>'
            f"{escape(item.label)}</a></li>"
        )
    return '<ul class="site-nav">' + "".join(items) + "</ul>"


def _home(state: BrowserSafeApplicationStateV1) -> tuple[str, str]:
    cards = []
    for task in state.home_tasks:
        status_class = "available" if task.available else "planned"
        cards.append(
            '<article class="task-card">'
            f'<p class="task-status {status_class}">{escape(task.availability)}</p>'
            f'<h2><a href="{escape(task.route, quote=True)}">{escape(task.title)}</a></h2>'
            f"<p>{escape(task.description)}</p>"
            '<dl class="task-details">'
            f"<dt>What you need</dt><dd>{escape(task.required_information)}</dd>"
            f"<dt>Mode</dt><dd>{escape(task.mode)}</dd>"
            f"<dt>Stored</dt><dd>{escape(task.storage)}</dd>"
            f"<dt>Result</dt><dd>{escape(task.expected_result)}</dd>"
            "</dl></article>"
        )
    content = (
        '<p class="lede">SkatMind runs locally on this computer and stores no data in '
        "the cloud.</p>"
        '<p class="supporting">Choose a task to see its current availability. Opening '
        "this shell does not load or analyze Product data.</p>"
        '<section class="task-grid" aria-label="SkatMind tasks">'
        + "".join(cards)
        + "</section>"
    )
    return "Home", content


def _placeholder(route: str) -> tuple[str, str]:
    pages = {
        "/analyze": (
            "Analyze a position",
            "Guided position analysis is available from the Analyze page.",
        ),
        "/review": (
            "Review a completed game",
            "Guided completed-game Review is available from the Review page.",
        ),
        "/sessions": (
            "Sessions",
            "Creating, opening, and resuming managed Sessions is not available in this shell "
            "yet. A later frontend update will add that lifecycle. The existing advanced "
            "Session CLI "
            "remains available.",
        ),
        "/matches": (
            "Match capture",
            "Managed Match listing and capture are not available in this shell yet. A later "
            "frontend update will integrate that lifecycle. The standalone advanced Capture "
            "interface "
            "remains available.",
        ),
        "/learning": (
            "Learning & cross-game insights",
            "Managed Corpus listing and Learning workflows are not available in this shell "
            "yet. A later frontend update will integrate that lifecycle. The standalone advanced "
            "Corpus "
            "interface remains available.",
        ),
    }
    title, description = pages[route]
    return title, (
        '<section class="placeholder" aria-labelledby="placeholder-status">'
        '<p id="placeholder-status" class="task-status planned">Not yet available</p>'
        f"<p>{escape(description)}</p>"
        '<p><a class="back-link" href="/">Return to Home</a></p>'
        "</section>"
    )


def _about(
    state: BrowserSafeApplicationStateV1,
    storage_root: Path,
) -> tuple[str, str]:
    content = (
        '<div class="about-grid">'
        '<section aria-labelledby="installation-heading">'
        '<h2 id="installation-heading">Installation</h2>'
        '<dl class="about-list">'
        f"<dt>Product</dt><dd>{escape(state.product_name)}</dd>"
        f"<dt>Package</dt><dd>Package {escape(state.package_version)}</dd>"
        "<dt>License</dt><dd>AGPL-3.0-only</dd>"
        "<dt>Copyright</dt><dd>Copyright (C) 2026 Henning Wiese</dd>"
        f"<dt>Current Python runtime</dt><dd>{escape(state.python_runtime)}</dd>"
        "<dt>Required Python</dt><dd>Python &gt;=3.13</dd>"
        "<dt>Certified boundary</dt><dd>CPython 3.13</dd>"
        "</dl></section>"
        '<section aria-labelledby="operation-heading">'
        '<h2 id="operation-heading">Local operation</h2>'
        "<p>SkatMind operates only on this computer. It uses no cloud or remote service "
        "and makes no external runtime requests.</p>"
        "<p>The managed home separates Sessions, Matches, and Corpora. Opening the shell "
        "creates only those directories and does not inspect their contents.</p>"
        '<details class="storage-disclosure"><summary>Show managed storage location</summary>'
        f"<code>{escape(str(storage_root), quote=True)}</code></details>"
        "</section>"
        '<section aria-labelledby="interfaces-heading">'
        '<h2 id="interfaces-heading">Advanced interfaces</h2>'
        "<p>The advanced command-line interfaces and Public Python API contract version 1 "
        "remain available.</p>"
        '<p>Current local documentation: <code>README.md</code>, '
        '<code>docs/installed_cli.md</code>, and '
        '<code>docs/public_python_api_v1.md</code>, and '
        '<code>docs/unified_local_frontend_contract.md</code>.</p>'
        "</section></div>"
    )
    return "About SkatMind", content


def render_app_page_v1(
    state: BrowserSafeApplicationStateV1,
    route: str,
    *,
    storage_root: Path | None = None,
    analyze_state: ProcessLocalFrontendWorkflowStateV1 | None = None,
    review_state: ProcessLocalFrontendWorkflowStateV1 | None = None,
) -> str:
    if type(state) is not BrowserSafeApplicationStateV1:
        raise ValueError("state must be an exact browser-safe application state.")
    if route not in APP_ROUTE_PATHS:
        raise ValueError("route must be a canonical application route.")
    if route != "/about" and storage_root is not None:
        raise ValueError("Private storage Path is allowed only on About.")
    if analyze_state is not None and type(analyze_state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("analyze_state must be exact process-local workflow state.")
    if review_state is not None and type(review_state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("review_state must be exact process-local workflow state.")
    if route == "/":
        title, content = _home(state)
    elif route == "/analyze":
        title = "Analyze a position"
        content = render_analyze_workflow_v1(
            analyze_state or ProcessLocalFrontendWorkflowStateV1()
        )
    elif route == "/review":
        title = "Review a completed game"
        content = render_review_workflow_v1(
            review_state or ProcessLocalFrontendWorkflowStateV1()
        )
    elif route == "/about":
        if not isinstance(storage_root, Path):
            raise ValueError("About rendering requires one private storage Path.")
        title, content = _about(state, storage_root)
    else:
        title, content = _placeholder(route)
    replacements = {
        "{{PAGE_TITLE}}": escape(title),
        "{{PRODUCT_NAME}}": escape(state.product_name),
        "{{NAVIGATION}}": _navigation(state, route),
        "{{HEADING}}": escape(title),
        "{{CONTENT}}": content,
    }
    rendered = _template()
    if any(marker not in rendered for marker in replacements):
        raise RuntimeError("Application template is missing a required marker.")
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    return rendered


def render_app_error_page_v1(
    state: BrowserSafeApplicationStateV1,
    *,
    title: str,
    message: str,
) -> str:
    rendered = _template()
    replacements = {
        "{{PAGE_TITLE}}": escape(title),
        "{{PRODUCT_NAME}}": escape(state.product_name),
        "{{NAVIGATION}}": _navigation(state, ""),
        "{{HEADING}}": escape(title),
        "{{CONTENT}}": (
            '<section class="placeholder">'
            f"<p>{escape(message)}</p>"
            '<p><a class="back-link" href="/">Return to Home</a></p>'
            "</section>"
        ),
    }
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    return rendered
