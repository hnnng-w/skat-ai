from __future__ import annotations

import re
from html import escape
from importlib.resources import files
from pathlib import Path

from .contracts import APP_ROUTE_PATHS, BrowserSafeApplicationStateV1
from .frontend_profile_operations import (
    FRONTEND_LANGUAGE_ACTION_ROUTE,
    FRONTEND_PROFILE_RESET_ACTION_ROUTE,
    is_safe_frontend_return_path_v1,
)
from .guided_rendering import render_analyze_workflow_v1, render_review_workflow_v1
from .information_architecture import (
    FRONTEND_EMPTY_STATE_KEYS,
    HOME_GROUP_TASK_MEMBERSHIP,
    HOME_RELATED_TASK_MEMBERSHIP,
    HOME_TASK_ROUTE_MAPPINGS,
    validate_frontend_information_architecture_v1,
)
from .localization_contracts import BrowserSafeFrontendProfileStateV1
from .translation_catalog import translate_frontend_message_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1

_WORKFLOW_ROUTES = {"/analyze", "/review", "/sessions", "/matches", "/learning"}
_PAGE_TITLE_KEYS = {
    "/": "page.home.title",
    "/analyze": "page.analyze.title",
    "/review": "page.review.title",
    "/sessions": "page.sessions.title",
    "/matches": "page.matches.title",
    "/learning": "page.learning.title",
    "/about": "page.about.title",
}
_CONCEPT_KEYS_BY_ROUTE = {
    "/analyze": "analyze",
    "/review": "review",
    "/sessions": "session",
    "/matches": "match",
    "/learning": "learning",
}


def _default_frontend_state() -> BrowserSafeFrontendProfileStateV1:
    return BrowserSafeFrontendProfileStateV1(
        locale="en",
        resolution_source="fallback",
        profile_status="absent",
        profile_revision=None,
        profile_generation=0,
        warning=False,
    )


def _template() -> str:
    return (
        files("skatmind.app_web")
        .joinpath("templates/app.html")
        .read_text(encoding="utf-8")
    )


def _text(
    frontend: BrowserSafeFrontendProfileStateV1,
    key: str,
    **values: object,
) -> str:
    return translate_frontend_message_v1(frontend.locale, key, **values)


def _translated(
    frontend: BrowserSafeFrontendProfileStateV1,
    key: str,
    **values: object,
) -> str:
    return escape(_text(frontend, key, **values))


def _navigation(
    state: BrowserSafeApplicationStateV1,
    current_route: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> str:
    items = []
    for item in state.navigation:
        current = ' aria-current="page"' if item.route == current_route else ""
        items.append(
            f'<li><a href="{escape(item.route, quote=True)}"{current}>'
            f"{_translated(frontend, item.message_key)}</a></li>"
        )
    return '<ul class="site-nav">' + "".join(items) + "</ul>"


def _language_selector(
    frontend: BrowserSafeFrontendProfileStateV1,
    return_to: str,
) -> str:
    if not is_safe_frontend_return_path_v1(return_to):
        raise ValueError("return_to must identify one safe rendered HTML path.")
    options = "".join(
        (
            f'<option value="{locale}"'
            f'{" selected" if frontend.locale == locale else ""}>'
            f'{_translated(frontend, f"common.language.{locale}")}</option>'
        )
        for locale in ("de", "en")
    )
    return (
        f'<form class="language-selector" method="post" '
        f'action="{FRONTEND_LANGUAGE_ACTION_ROUTE}" '
        f'aria-label="{_translated(frontend, "language.selector_label")}">'
        f'<label><span>{_translated(frontend, "language.select_label")}</span>'
        f'<select name="language">{options}</select></label>'
        f'<input type="hidden" name="profile_generation" '
        f'value="{frontend.profile_generation}">'
        f'<input type="hidden" name="return_to" value="{escape(return_to, quote=True)}">'
        f'<button type="submit">{_translated(frontend, "language.apply")}</button>'
        "</form>"
    )


def _home(
    state: BrowserSafeApplicationStateV1,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> tuple[str, str]:
    validate_frontend_information_architecture_v1()
    task_routes = dict(HOME_TASK_ROUTE_MAPPINGS)
    state_tasks = {task.route: task for task in state.home_tasks}
    if set(state_tasks) != set(task_routes.values()):
        raise ValueError("Browser-safe Home tasks must cover each IA task Route.")

    scope_items = []
    for scope_key, task_key in (
        ("decision", "analyze_decision"),
        ("session", "record_session"),
        ("review", "review_game"),
        ("match", "record_match"),
        ("learning", "learning_insights"),
    ):
        route = task_routes[task_key]
        scope_items.append(
            f'<dt>{_translated(frontend, f"home.scope_guide.{scope_key}.unit")}</dt>'
            f'<dd><a href="{escape(route, quote=True)}">'
            f'{_translated(frontend, f"home.scope_guide.{scope_key}.action")}</a> '
            f'{_translated(frontend, f"home.scope_guide.{scope_key}.description")}</dd>'
        )
    scope_guide = (
        '<section class="scope-guide" aria-labelledby="scope-guide-heading">'
        f'<h2 id="scope-guide-heading">'
        f'{_translated(frontend, "home.scope_guide.heading")}</h2>'
        f'<p>{_translated(frontend, "home.scope_guide.introduction")}</p>'
        f'<dl class="scope-guide-list">{"".join(scope_items)}</dl>'
        f'<p class="scope-distinction">'
        f'{_translated(frontend, "home.scope_guide.distinction")}</p></section>'
    )

    groups = []
    for group_key, task_keys in HOME_GROUP_TASK_MEMBERSHIP:
        cards = []
        for task_key in task_keys:
            route = task_routes[task_key]
            task = state_tasks[route]
            if not task.available:
                raise ValueError("Issue-#217 Home tasks must remain available.")
            prefix = f"home.task.{task_key}"
            cards.append(
                '<article class="task-card">'
                f'<h3>{_translated(frontend, f"{prefix}.title")}</h3>'
                f'<p class="task-summary">{_translated(frontend, f"{prefix}.summary")}</p>'
                '<dl class="task-scope">'
                f'<dt>{_translated(frontend, "home.details.unit")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.unit")}</dd>'
                f'<dt>{_translated(frontend, "home.details.timing")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.timing")}</dd></dl>'
                '<details class="task-disclosure"><summary>'
                f'{_translated(frontend, "home.details.more")}</summary>'
                '<dl class="task-details">'
                f'<dt>{_translated(frontend, "home.details.when")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.when")}</dd>'
                f'<dt>{_translated(frontend, "home.details.required")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.required")}</dd>'
                f'<dt>{_translated(frontend, "home.details.storage")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.storage")}</dd>'
                f'<dt>{_translated(frontend, "home.details.result")}</dt>'
                f'<dd>{_translated(frontend, f"{prefix}.result")}</dd></dl></details>'
                f'<p class="task-action"><a class="button-link" '
                f'href="{escape(route, quote=True)}">'
                f'{_translated(frontend, f"{prefix}.action")}</a></p></article>'
            )
        heading_id = f"home-group-{group_key}"
        groups.append(
            f'<section class="home-group" aria-labelledby="{heading_id}">'
            f'<h2 id="{heading_id}">'
            f'{_translated(frontend, f"home.group.{group_key}.title")}</h2>'
            f'<p>{_translated(frontend, f"home.group.{group_key}.description")}</p>'
            f'<div class="task-grid">{"".join(cards)}</div></section>'
        )
    content = (
        f'<p class="lede">{_translated(frontend, "home.introduction")}</p>'
        f'<p class="supporting">{_translated(frontend, "home.supporting")}</p>'
        f"{scope_guide}{''.join(groups)}"
    )
    return _text(frontend, "page.home.title"), content


def _related_areas(
    route: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> str:
    task_routes = dict(HOME_TASK_ROUTE_MAPPINGS)
    source_task = next(
        task_key
        for task_key, task_route in HOME_TASK_ROUTE_MAPPINGS
        if task_route == route
    )
    related = dict(HOME_RELATED_TASK_MEMBERSHIP).get(source_task, ())
    if not related:
        return ""
    links = "".join(
        f'<li><a href="{escape(task_routes[task_key], quote=True)}">'
        f'{_translated(frontend, f"related.{task_key}")}</a></li>'
        for task_key in related
    )
    return (
        '<section class="related-areas" aria-labelledby="related-areas-heading">'
        f'<h2 id="related-areas-heading">{_translated(frontend, "related.heading")}</h2>'
        f"<ul>{links}</ul></section>"
    )


def _workflow_concept(
    route: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> str:
    concept_key = _CONCEPT_KEYS_BY_ROUTE[route]
    steps = ""
    if route == "/learning":
        steps = (
            f'<h3>{_translated(frontend, "concept.learning.steps.heading")}</h3>'
            '<ol class="learning-steps">'
            + "".join(
                f'<li>{_translated(frontend, f"concept.learning.steps.{step}")}</li>'
                for step in ("record", "add", "select", "build", "review")
            )
            + "</ol>"
            f'<p>{_translated(frontend, "concept.learning.automatic")}</p>'
        )
    return (
        f'<section class="concept-guide" aria-labelledby="concept-{concept_key}-heading">'
        f'<p class="eyebrow">{_translated(frontend, f"concept.{concept_key}.scope")}</p>'
        f'<h2 id="concept-{concept_key}-heading">'
        f'{_translated(frontend, f"concept.{concept_key}.heading")}</h2>'
        f'<p class="concept-timing">'
        f'{_translated(frontend, f"concept.{concept_key}.timing")}</p>'
        f'<p>{_translated(frontend, f"concept.{concept_key}.description")}</p>'
        f'<p>{_translated(frontend, f"concept.{concept_key}.detail")}</p>'
        f"{steps}</section>{_related_areas(route, frontend)}"
    )


def _empty_state(
    empty_state_key: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> str:
    if empty_state_key not in FRONTEND_EMPTY_STATE_KEYS:
        raise ValueError("empty_state_key must identify one canonical empty state.")
    prefix = f"empty.{empty_state_key}"
    return (
        f'<section class="guided-empty-state" aria-labelledby="empty-{empty_state_key}-heading">'
        f'<h2 id="empty-{empty_state_key}-heading">'
        f'{_translated(frontend, f"{prefix}.heading")}</h2>'
        f'<p>{_translated(frontend, f"{prefix}.description")}</p>'
        f'<p>{_translated(frontend, f"{prefix}.next")}</p></section>'
    )


def _placeholder(
    route: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> tuple[str, str]:
    title = _text(frontend, _PAGE_TITLE_KEYS[route])
    return title, (
        '<section class="placeholder" aria-labelledby="placeholder-status">'
        '<p id="placeholder-status" class="task-status available">'
        f'<span>{_translated(frontend, "status.label")}:</span> '
        f'{_translated(frontend, "placeholder.available")}</p>'
        f'<p><a class="back-link" href="/">'
        f'{_translated(frontend, "placeholder.return")}</a></p>'
        "</section>"
    )


def _profile_about_section(frontend: BrowserSafeFrontendProfileStateV1) -> str:
    language = _translated(frontend, f"common.language.{frontend.locale}")
    source = _translated(frontend, f"profile.source.{frontend.resolution_source}")
    status = _translated(frontend, f"profile.status.{frontend.profile_status}")
    return (
        '<section aria-labelledby="profile-heading">'
        f'<h2 id="profile-heading">{_translated(frontend, "about.profile.heading")}</h2>'
        f'<p>{_translated(frontend, "about.profile.private")}</p>'
        f'<p>{_translated(frontend, "about.profile.no_cloud")}</p>'
        '<dl class="about-list">'
        f'<dt>{_translated(frontend, "about.profile.current_language")}</dt>'
        f"<dd>{language}</dd>"
        f'<dt>{_translated(frontend, "about.profile.language_source")}</dt>'
        f"<dd>{source}</dd>"
        f'<dt>{_translated(frontend, "about.profile.status")}</dt>'
        f"<dd>{status}</dd></dl>"
        f'<p>{_translated(frontend, "about.profile.future")}</p>'
        f'<form class="reset-form" method="post" '
        f'action="{FRONTEND_PROFILE_RESET_ACTION_ROUTE}">'
        f'<input type="hidden" name="profile_generation" '
        f'value="{frontend.profile_generation}">'
        '<input type="hidden" name="return_to" value="/about">'
        f'<p>{_translated(frontend, "profile.reset.description")}</p>'
        f'<label><input type="checkbox" name="confirm_reset" value="on" required> '
        f'{_translated(frontend, "profile.reset.confirm")}</label>'
        f'<button type="submit">{_translated(frontend, "profile.reset.submit")}</button>'
        "</form></section>"
    )


def _about(
    state: BrowserSafeApplicationStateV1,
    storage_root: Path,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> tuple[str, str]:
    package_value = _translated(
        frontend,
        "about.installation.package_value",
        version=state.package_version,
    )
    content = (
        '<div class="about-grid">'
        '<section aria-labelledby="installation-heading">'
        f'<h2 id="installation-heading">'
        f'{_translated(frontend, "about.installation.heading")}</h2>'
        '<dl class="about-list">'
        f'<dt>{_translated(frontend, "about.installation.product")}</dt>'
        f"<dd>{escape(state.product_name)}</dd>"
        f'<dt>{_translated(frontend, "about.installation.package")}</dt>'
        f"<dd>{package_value}</dd>"
        f'<dt>{_translated(frontend, "about.installation.license")}</dt>'
        "<dd>AGPL-3.0-only</dd>"
        f'<dt>{_translated(frontend, "about.installation.copyright")}</dt>'
        "<dd>Copyright (C) 2026 Henning Wiese</dd>"
        f'<dt>{_translated(frontend, "about.installation.current_python")}</dt>'
        f"<dd>{escape(state.python_runtime)}</dd>"
        f'<dt>{_translated(frontend, "about.installation.required_python")}</dt>'
        "<dd>Python &gt;=3.13</dd>"
        f'<dt>{_translated(frontend, "about.installation.certified_boundary")}</dt>'
        "<dd>CPython 3.13</dd>"
        "</dl></section>"
        '<section aria-labelledby="operation-heading">'
        f'<h2 id="operation-heading">{_translated(frontend, "about.local.heading")}</h2>'
        f'<p>{_translated(frontend, "about.local.description")}</p>'
        f'<p>{_translated(frontend, "about.local.managed_home")}</p>'
        '<details class="storage-disclosure"><summary>'
        f'{_translated(frontend, "about.local.storage_show")}</summary>'
        f"<code>{escape(str(storage_root), quote=True)}</code></details>"
        "</section>"
        f"{_profile_about_section(frontend)}"
        '<section aria-labelledby="interfaces-heading">'
        f'<h2 id="interfaces-heading">{_translated(frontend, "about.advanced.heading")}</h2>'
        f'<p>{_translated(frontend, "about.advanced.description")}</p>'
        f'<p>{_translated(frontend, "about.advanced.documentation")}: '
        '<code>README.md</code>, <code>docs/installed_cli.md</code>, '
        '<code>docs/public_python_api_v1.md</code>, '
        '<code>docs/unified_local_frontend_contract.md</code>.</p>'
        "</section></div>"
    )
    return _text(frontend, "page.about.title"), content


def _workflow_boundary(
    content: str,
    frontend: BrowserSafeFrontendProfileStateV1,
) -> str:
    if frontend.locale != "de":
        return content
    return (
        '<aside class="translation-status" role="status">'
        f'{_translated(frontend, "translation.english_body_notice")}</aside>'
        f'<div class="english-workflow-body" lang="en">{content}</div>'
    )


def _shell(
    state: BrowserSafeApplicationStateV1,
    route: str,
    *,
    title: str,
    content: str,
    frontend: BrowserSafeFrontendProfileStateV1,
    return_to: str,
    extra_stylesheets: tuple[str, ...],
    extra_scripts: tuple[str, ...],
) -> str:
    warning = (
        '<aside class="profile-warning" role="alert">'
        f'{_translated(frontend, "profile.invalid_warning")}</aside>'
        if frontend.warning
        else ""
    )
    replacements = {
        "{{HTML_LANG}}": escape(frontend.locale, quote=True),
        "{{PAGE_TITLE}}": escape(title),
        "{{PRODUCT_NAME}}": escape(state.product_name),
        "{{SKIP_LINK}}": _translated(frontend, "shell.skip_link"),
        "{{BRAND_LABEL}}": _translated(frontend, "shell.brand_label"),
        "{{NAVIGATION_LABEL}}": _translated(frontend, "navigation.label"),
        "{{NAVIGATION}}": _navigation(state, route, frontend),
        "{{LANGUAGE_SELECTOR}}": _language_selector(frontend, return_to),
        "{{HEADING}}": escape(title),
        "{{PROFILE_WARNING}}": warning,
        "{{CONTENT}}": content,
        "{{FOOTER}}": _translated(frontend, "footer.local_no_cloud"),
        "{{EXTRA_STYLES}}": "".join(
            f'<link rel="stylesheet" href="{escape(path, quote=True)}">'
            for path in extra_stylesheets
        ),
        "{{EXTRA_SCRIPTS}}": "".join(
            f'<script src="{escape(path, quote=True)}" defer></script>'
            for path in extra_scripts
        ),
    }
    template = _template()
    if any(marker not in template for marker in replacements):
        raise RuntimeError("Application template is missing a required marker.")
    marker_pattern = re.compile("|".join(re.escape(marker) for marker in replacements))
    return marker_pattern.sub(lambda match: replacements[match.group(0)], template)


def render_app_page_v1(
    state: BrowserSafeApplicationStateV1,
    route: str,
    *,
    storage_root: Path | None = None,
    analyze_state: ProcessLocalFrontendWorkflowStateV1 | None = None,
    review_state: ProcessLocalFrontendWorkflowStateV1 | None = None,
    frontend: BrowserSafeFrontendProfileStateV1 | None = None,
    return_to: str | None = None,
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
    frontend_state = frontend or _default_frontend_state()
    if route == "/":
        title, content = _home(state, frontend_state)
    elif route == "/analyze":
        title = _text(frontend_state, "page.analyze.title")
        content = render_analyze_workflow_v1(
            analyze_state or ProcessLocalFrontendWorkflowStateV1()
        )
    elif route == "/review":
        title = _text(frontend_state, "page.review.title")
        content = render_review_workflow_v1(
            review_state or ProcessLocalFrontendWorkflowStateV1()
        )
    elif route == "/about":
        if not isinstance(storage_root, Path):
            raise ValueError("About rendering requires one private storage Path.")
        title, content = _about(state, storage_root, frontend_state)
    else:
        title, content = _placeholder(route, frontend_state)
    if route in _WORKFLOW_ROUTES:
        content = _workflow_concept(route, frontend_state) + _workflow_boundary(
            content,
            frontend_state,
        )
    return _shell(
        state,
        route,
        title=title,
        content=content,
        frontend=frontend_state,
        return_to=return_to or route,
        extra_stylesheets=(),
        extra_scripts=(),
    )


def render_app_content_page_v1(
    state: BrowserSafeApplicationStateV1,
    route: str,
    *,
    title: str | None = None,
    title_key: str | None = None,
    content: str,
    frontend: BrowserSafeFrontendProfileStateV1 | None = None,
    return_to: str | None = None,
    untranslated_workflow_body: bool = True,
    empty_state_key: str | None = None,
    extra_stylesheets: tuple[str, ...] = (),
    extra_scripts: tuple[str, ...] = (),
) -> str:
    """Renders trusted server-built stateful content inside the canonical shell."""

    if type(state) is not BrowserSafeApplicationStateV1:
        raise ValueError("state must be an exact browser-safe application state.")
    if route not in APP_ROUTE_PATHS:
        raise ValueError("route must be a canonical application route.")
    if (title is None) == (title_key is None) or type(content) is not str:
        raise ValueError("Provide exactly one shell title or title message key.")
    if title is not None and (type(title) is not str or not title):
        raise ValueError("Shell title must be non-empty text.")
    if title_key is not None and (type(title_key) is not str or not title_key):
        raise ValueError("Shell title message key must be non-empty text.")
    if any(
        type(path) is not str or not path.startswith("/") or '"' in path
        for path in (*extra_stylesheets, *extra_scripts)
    ):
        raise ValueError("Extra assets must use safe absolute local routes.")
    frontend_state = frontend or _default_frontend_state()
    resolved_title = (
        _text(frontend_state, title_key) if title_key is not None else str(title)
    )
    if empty_state_key is not None and route not in _WORKFLOW_ROUTES:
        raise ValueError("Empty-state guidance belongs only to workflow Routes.")
    localized_content = ""
    if route in _WORKFLOW_ROUTES:
        localized_content = _workflow_concept(route, frontend_state)
        if empty_state_key is not None:
            localized_content += _empty_state(empty_state_key, frontend_state)
    rendered_content = localized_content + (
        _workflow_boundary(content, frontend_state)
        if untranslated_workflow_body and route in _WORKFLOW_ROUTES
        else content
    )
    return _shell(
        state,
        route,
        title=resolved_title,
        content=rendered_content,
        frontend=frontend_state,
        return_to=return_to or route,
        extra_stylesheets=extra_stylesheets,
        extra_scripts=extra_scripts,
    )


def render_app_error_page_v1(
    state: BrowserSafeApplicationStateV1,
    *,
    title: str | None = None,
    message: str | None = None,
    title_key: str | None = None,
    message_key: str | None = None,
    frontend: BrowserSafeFrontendProfileStateV1 | None = None,
    return_to: str = "/",
    untranslated_message: bool = False,
) -> str:
    if (title is None) == (title_key is None) or (message is None) == (message_key is None):
        raise ValueError("Error rendering requires one title and one message authority.")
    if title is not None and (type(title) is not str or not title):
        raise ValueError("Error title must be non-empty text.")
    if title_key is not None and (type(title_key) is not str or not title_key):
        raise ValueError("Error title message key must be non-empty text.")
    if message is not None and type(message) is not str:
        raise ValueError("Error message must be text.")
    if message_key is not None and (type(message_key) is not str or not message_key):
        raise ValueError("Error message key must be non-empty text.")
    frontend_state = frontend or _default_frontend_state()
    resolved_title = (
        _text(frontend_state, title_key) if title_key is not None else str(title)
    )
    resolved_message = (
        _translated(frontend_state, message_key)
        if message_key is not None
        else escape(str(message))
    )
    if untranslated_message and frontend_state.locale == "de":
        resolved_message = (
            '<div lang="en" class="english-workflow-body">'
            f"{resolved_message}</div>"
        )
    content = (
        '<section class="placeholder">'
        f"<p>{resolved_message}</p>"
        f'<p><a class="back-link" href="/">'
        f'{_translated(frontend_state, "common.action.return_home")}</a></p>'
        "</section>"
    )
    return _shell(
        state,
        "",
        title=resolved_title,
        content=content,
        frontend=frontend_state,
        return_to=return_to,
        extra_stylesheets=(),
        extra_scripts=(),
    )


def render_authorization_failure_v1(frontend: BrowserSafeFrontendProfileStateV1) -> str:
    if type(frontend) is not BrowserSafeFrontendProfileStateV1:
        raise ValueError("frontend must be exact browser-safe locale state.")
    return (
        "<!doctype html>\n"
        f'<html lang="{escape(frontend.locale, quote=True)}">\n'
        "<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{_translated(frontend, 'authorization.heading')}</title>\n"
        "</head>\n<body>\n<main>\n"
        f"<h1>{_translated(frontend, 'authorization.heading')}</h1>\n"
        f"<p>{_translated(frontend, 'authorization.message')}</p>\n"
        f"<p>{_translated(frontend, 'authorization.next_step')}</p>\n"
        "</main>\n</body>\n</html>\n"
    )
