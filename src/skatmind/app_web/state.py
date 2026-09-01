from __future__ import annotations

import platform

from skatmind import __version__

from .contracts import (
    APP_HOME_TASK_MESSAGE_KEY_PREFIXES,
    APP_NAVIGATION_MESSAGE_KEYS,
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
        NavigationItemV1(route=route, message_key=message_key)
        for route, message_key in zip(
            APP_ROUTE_PATHS,
            APP_NAVIGATION_MESSAGE_KEYS,
            strict=True,
        )
    )
    tasks = tuple(
        HomeTaskV1(
            route=route,
            title_message_key=f"{prefix}.title",
            description_message_key=f"{prefix}.description",
            required_information_message_key=f"{prefix}.required",
            storage_message_key=f"{prefix}.storage",
            mode_message_key=f"{prefix}.mode",
            expected_result_message_key=f"{prefix}.result",
            available=True,
            availability_message_key=f"{prefix}.availability",
        )
        for route, prefix in zip(
            APP_ROUTE_PATHS[1:],
            APP_HOME_TASK_MESSAGE_KEY_PREFIXES,
            strict=True,
        )
    )
    return BrowserSafeApplicationStateV1(
        product_name="SkatMind",
        package_version=__version__,
        python_runtime=f"{platform.python_implementation()} {platform.python_version()}",
        navigation=navigation,
        home_tasks=tasks,
    )
