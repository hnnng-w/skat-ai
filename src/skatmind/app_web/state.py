from __future__ import annotations

import platform

from skatmind import __version__

from .contracts import (
    APP_HOME_TASK_TITLES,
    APP_NAVIGATION_LABELS,
    APP_ROUTE_PATHS,
    BrowserSafeApplicationStateV1,
    HomeTaskV1,
    NavigationItemV1,
    validate_unified_local_frontend_contract_v1,
)


def build_browser_safe_application_state_v1() -> BrowserSafeApplicationStateV1:
    """Builds the immutable shell projection without private runtime values."""

    validate_unified_local_frontend_contract_v1()
    navigation = tuple(
        NavigationItemV1(route=route, label=label)
        for route, label in zip(APP_ROUTE_PATHS, APP_NAVIGATION_LABELS, strict=True)
    )
    tasks = (
        HomeTaskV1(
            route="/analyze",
            title=APP_HOME_TASK_TITLES[0],
            description="Get guidance for the next card in a current Skat position.",
            required_information="Your hand, the contract, the current trick, and visible play.",
            storage="The shell stores no position or Result.",
            mode="Live",
            expected_result="A recommendation and explanation will be added in Issue #211.",
            available=False,
            availability="Guided workflow not yet available. Planned for Issue #211.",
        ),
        HomeTaskV1(
            route="/review",
            title=APP_HOME_TASK_TITLES[1],
            description="Review decisions from one completed Skat game.",
            required_information="The completed game record and declaration.",
            storage="The shell stores no game or Review Result.",
            mode="Retrospective",
            expected_result="A readable game Review will be added in Issue #211.",
            available=False,
            availability="Guided workflow not yet available. Planned for Issue #211.",
        ),
        HomeTaskV1(
            route="/sessions",
            title=APP_HOME_TASK_TITLES[2],
            description="Capture a game step by step for later analysis or Review.",
            required_information="Three Players and the observed bidding, declaration, and play.",
            storage="Sessions will use the managed sessions category.",
            mode="Live or Retrospective",
            expected_result="A resumable Session lifecycle will be added in Issue #212.",
            available=False,
            availability="Managed Session workflow not yet available. Planned for Issue #212.",
        ),
        HomeTaskV1(
            route="/matches",
            title=APP_HOME_TASK_TITLES[3],
            description="Capture the 36 positions of one EuroSkat Standard Match.",
            required_information="Match participants and observed deal evidence.",
            storage="Matches will use the managed matches category.",
            mode="Retrospective",
            expected_result="A managed Match capture lifecycle will be added in Issue #212.",
            available=False,
            availability="Managed Match workflow not yet available. Planned for Issue #212.",
        ),
        HomeTaskV1(
            route="/learning",
            title=APP_HOME_TASK_TITLES[4],
            description="Explore learning evidence and cross-game summaries.",
            required_information="Captured Matches and selected analysis evidence.",
            storage="Learning data will use the managed corpora category.",
            mode="Retrospective",
            expected_result="A managed Learning lifecycle will be added in Issue #212.",
            available=False,
            availability="Managed Learning workflow not yet available. Planned for Issue #212.",
        ),
        HomeTaskV1(
            route="/about",
            title=APP_HOME_TASK_TITLES[5],
            description="Read the local runtime, license, storage, and interface boundaries.",
            required_information="No Product data is required.",
            storage="Opening About stores no Product data.",
            mode="Reference",
            expected_result="Local installation and documentation information.",
            available=True,
            availability="Available now.",
        ),
    )
    return BrowserSafeApplicationStateV1(
        product_name="SkatMind",
        package_version=__version__,
        python_runtime=f"{platform.python_implementation()} {platform.python_version()}",
        navigation=navigation,
        home_tasks=tasks,
    )
