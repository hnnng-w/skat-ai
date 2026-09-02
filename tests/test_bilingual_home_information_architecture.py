from __future__ import annotations

from dataclasses import asdict

import pytest

import skatmind
import skatmind.api.v1 as public_api
from skatmind.app_web.information_architecture import (
    FRONTEND_EMPTY_STATE_KEYS,
    FRONTEND_INFORMATION_ARCHITECTURE_VERSION,
    HOME_GROUP_KEYS,
    HOME_GROUP_TASK_MEMBERSHIP,
    HOME_RELATED_TASK_MEMBERSHIP,
    HOME_TASK_KEYS,
    HOME_TASK_ROUTE_MAPPINGS,
    validate_frontend_information_architecture_v1,
)
from skatmind.app_web.localization_contracts import BrowserSafeFrontendProfileStateV1
from skatmind.app_web.rendering import render_app_content_page_v1, render_app_page_v1
from skatmind.app_web.state import build_browser_safe_application_state_v1


def _frontend(locale: str) -> BrowserSafeFrontendProfileStateV1:
    return BrowserSafeFrontendProfileStateV1(
        locale=locale,
        resolution_source="fallback" if locale == "en" else "browser",
        profile_status="absent",
        profile_revision=None,
        profile_generation=0,
        warning=False,
    )


def test_information_architecture_contract_values_are_exact_and_private() -> None:
    assert FRONTEND_INFORMATION_ARCHITECTURE_VERSION == 1
    assert HOME_GROUP_KEYS == (
        "record_games",
        "analyze_and_review",
        "learn_across_matches",
        "product_information",
    )
    assert HOME_TASK_KEYS == (
        "record_match",
        "record_session",
        "analyze_decision",
        "review_game",
        "learning_insights",
        "about",
    )
    assert HOME_TASK_ROUTE_MAPPINGS == (
        ("record_match", "/matches"),
        ("record_session", "/sessions"),
        ("analyze_decision", "/analyze"),
        ("review_game", "/review"),
        ("learning_insights", "/learning"),
        ("about", "/about"),
    )
    assert HOME_GROUP_TASK_MEMBERSHIP == (
        ("record_games", ("record_match", "record_session")),
        ("analyze_and_review", ("analyze_decision", "review_game")),
        ("learn_across_matches", ("learning_insights",)),
        ("product_information", ("about",)),
    )
    assert HOME_RELATED_TASK_MEMBERSHIP == (
        ("analyze_decision", ("review_game",)),
        ("review_game", ("analyze_decision", "record_match")),
        ("record_session", ("record_match",)),
        ("record_match", ("record_session", "learning_insights")),
        ("learning_insights", ("record_match",)),
    )
    assert FRONTEND_EMPTY_STATE_KEYS == (
        "sessions",
        "matches",
        "learning_collections",
        "learning_data",
    )
    validate_frontend_information_architecture_v1()
    for name in (
        "FRONTEND_INFORMATION_ARCHITECTURE_VERSION",
        "HOME_GROUP_KEYS",
        "HOME_TASK_KEYS",
    ):
        assert name not in skatmind.__all__ and not hasattr(skatmind, name)
        assert name not in public_api.__all__ and not hasattr(public_api, name)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("version", True),
        ("version", 2),
        ("group_keys", tuple(reversed(HOME_GROUP_KEYS))),
        ("group_keys", (*HOME_GROUP_KEYS, "extra")),
        ("task_keys", (*HOME_TASK_KEYS[:-1], HOME_TASK_KEYS[0])),
        ("task_keys", HOME_TASK_KEYS[:-1]),
        ("task_routes", tuple(reversed(HOME_TASK_ROUTE_MAPPINGS))),
        (
            "task_routes",
            (*HOME_TASK_ROUTE_MAPPINGS[:-1], ("orphan", "/about")),
        ),
        ("group_membership", tuple(reversed(HOME_GROUP_TASK_MEMBERSHIP))),
        (
            "group_membership",
            (*HOME_GROUP_TASK_MEMBERSHIP[:-1], ("product_information", ())),
        ),
    ),
)
def test_information_architecture_rejects_drift(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        validate_frontend_information_architecture_v1(**{field_name: value})


@pytest.mark.parametrize(
    ("locale", "group_headings", "task_titles", "guide_heading"),
    (
        (
            "en",
            (
                "Record games",
                "Analyze and review",
                "Learn across Matches",
                "Product information",
            ),
            (
                "Record a complete 36-game Match",
                "Record or continue one individual game",
                "Analyze one decision",
                "Review one completed individual game",
                "Explore patterns across recorded Matches",
                "About SkatMind",
            ),
            "Which area do I need?",
        ),
        (
            "de",
            (
                "Spiele erfassen",
                "Analysieren und auswerten",
                "Über mehrere Matches lernen",
                "Produktinformationen",
            ),
            (
                "Ein vollständiges 36er-Match erfassen",
                "Ein einzelnes Spiel erfassen oder fortsetzen",
                "Eine Entscheidung analysieren",
                "Ein abgeschlossenes einzelnes Spiel auswerten",
                "Muster über erfasste Matches hinweg untersuchen",
                "Über SkatMind",
            ),
            "Welchen Bereich brauche ich?",
        ),
    ),
)
def test_home_groups_match_first_scope_guide_and_compact_cards(
    locale: str,
    group_headings: tuple[str, ...],
    task_titles: tuple[str, ...],
    guide_heading: str,
) -> None:
    state = build_browser_safe_application_state_v1()
    retained_state = asdict(state)
    html = render_app_page_v1(state, "/", frontend=_frontend(locale))
    main = html[html.index("<main") : html.index("</main>")]
    groups_html = main[main.index('<section class="home-group"') :]

    assert f'<html lang="{locale}">' in html
    assert html.count('<section class="home-group"') == 4
    assert html.count('<article class="task-card">') == 6
    assert html.count('<details class="task-disclosure">') == 6
    assert '<details class="task-disclosure" open' not in html
    assert html.count('class="task-scope"') == 6
    assert html.count('class="task-action"') == 6
    assert guide_heading in html
    scope_guide = main.split('<section class="scope-guide"', 1)[1].split(
        "</section>",
        1,
    )[0]
    for forbidden in (
        "JSON",
        "Search",
        "Dataset",
        "Snapshot",
        "seed",
        "sample",
        "Policy",
        "Provenance",
    ):
        assert forbidden not in scope_guide
    assert [groups_html.index(value) for value in group_headings] == sorted(
        groups_html.index(value) for value in group_headings
    )
    assert [groups_html.index(value) for value in task_titles] == sorted(
        groups_html.index(value) for value in task_titles
    )
    assert groups_html.index(task_titles[0]) < groups_html.index(task_titles[1])
    assert groups_html.index('href="/matches"') < groups_html.index('href="/sessions"')
    assert "Available now." not in html and "Jetzt verfügbar." not in html
    assert "Live</dd>" not in html
    assert "english-workflow-body" not in html
    assert asdict(state) == retained_state


def test_product_concepts_and_related_routes_are_localized_without_mutation() -> None:
    state = build_browser_safe_application_state_v1()
    expected = {
        "/analyze": ('href="/review"',),
        "/review": ('href="/analyze"', 'href="/matches"'),
        "/sessions": ('href="/matches"',),
        "/matches": ('href="/sessions"', 'href="/learning"'),
        "/learning": ('href="/matches"',),
    }
    for route, links in expected.items():
        html = render_app_content_page_v1(
            state,
            route,
            title="Retained workflow title",
            content="<p>Untranslated workflow form</p>",
            frontend=_frontend("en"),
        )
        related = html.split('<section class="related-areas"', 1)[1].split(
            "</section>",
            1,
        )[0]
        assert tuple(link for link in links if link in related) == links
        assert related.count("href=") == len(links)
        assert "?" not in related
        assert "Untranslated workflow form" in html

    analyze = render_app_page_v1(state, "/analyze", frontend=_frontend("en"))
    assert "Current or retrospective" in analyze
    assert "one choice of Card" in analyze
    review = render_app_page_v1(state, "/review", frontend=_frontend("en"))
    for value in (
        "one completed individual Skat game",
        "recorded Decisions",
        "alternatives",
        "Result",
        "Overbid",
        "Settlement",
        "complete 36-position list",
    ):
        assert value in review

    german = render_app_content_page_v1(
        state,
        "/sessions",
        title="Retained workflow title",
        content="<p>Future-owned English form</p>",
        frontend=_frontend("de"),
        empty_state_key="sessions",
    )
    assert "Ein fortsetzbares einzelnes Spiel" in german
    assert "nicht automatisch in ein Match eingefügt" in german
    assert "Noch keine erfassten einzelnen Spiele" in german
    assert german.index("Noch keine erfassten einzelnen Spiele") < german.index(
        '<div class="english-workflow-body" lang="en">'
    )
    assert (
        '<div class="english-workflow-body" lang="en">'
        "<p>Future-owned English form</p></div>"
        in german
    )
