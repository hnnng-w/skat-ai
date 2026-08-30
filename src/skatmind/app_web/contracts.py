from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

UNIFIED_LOCAL_FRONTEND_CONTRACT_VERSION = 1
LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION = 1
MANAGED_LOCAL_DATA_CONTRACT_VERSION = 1

UNIFIED_LOCAL_FRONTEND_POLICIES = (
    "bare_skatmind_opens_unified_local_frontend",
    "one_loopback_server_one_browser_application",
    "managed_local_data_without_required_user_paths",
    "guided_normal_workflows_with_advanced_settings_separated",
    "human_readable_results_with_optional_json_import_and_export",
    "reuse_existing_application_session_match_and_corpus_contracts",
    "no_product_semantics_change_from_frontend_translation",
    "no_external_frontend_resources_or_runtime_requests",
    "advanced_cli_and_public_python_api_remain_supported",
    "existing_private_information_boundaries_remain_authoritative",
)

APP_ROUTE_PATHS = (
    "/",
    "/analyze",
    "/review",
    "/sessions",
    "/matches",
    "/learning",
    "/about",
)
APP_NAVIGATION_LABELS = (
    "Home",
    "Analyze a position",
    "Review a completed game",
    "Sessions",
    "Match capture",
    "Learning & cross-game insights",
    "About SkatMind",
)
APP_HOME_TASK_TITLES = (
    "Analyze a position",
    "Review a completed game",
    "Create or resume a Session",
    "Capture a 36-game Match",
    "Open Learning & cross-game insights",
    "About SkatMind",
)
MANAGED_LOCAL_DATA_CATEGORIES = (
    "sessions",
    "matches",
    "corpora",
)


def _require_text(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be non-empty text.")


def _require_exact_ordered_values(
    value: object,
    expected: tuple[str, ...],
    name: str,
) -> None:
    if type(value) is not tuple or value != expected:
        raise ValueError(f"{name} must contain the exact canonical ordered values.")


def validate_unified_local_frontend_contract_v1(
    *,
    policies: tuple[str, ...] = UNIFIED_LOCAL_FRONTEND_POLICIES,
    routes: tuple[str, ...] = APP_ROUTE_PATHS,
    navigation_labels: tuple[str, ...] = APP_NAVIGATION_LABELS,
    home_tasks: tuple[str, ...] = APP_HOME_TASK_TITLES,
    managed_categories: tuple[str, ...] = MANAGED_LOCAL_DATA_CATEGORIES,
) -> None:
    """Rejects any drift in the frozen Issue-#209 ordered values."""

    _require_exact_ordered_values(
        policies,
        UNIFIED_LOCAL_FRONTEND_POLICIES,
        "policies",
    )
    _require_exact_ordered_values(routes, APP_ROUTE_PATHS, "routes")
    _require_exact_ordered_values(
        navigation_labels,
        APP_NAVIGATION_LABELS,
        "navigation_labels",
    )
    _require_exact_ordered_values(home_tasks, APP_HOME_TASK_TITLES, "home_tasks")
    _require_exact_ordered_values(
        managed_categories,
        MANAGED_LOCAL_DATA_CATEGORIES,
        "managed_categories",
    )
    for name, values in (
        ("policies", policies),
        ("routes", routes),
        ("navigation_labels", navigation_labels),
        ("home_tasks", home_tasks),
        ("managed_categories", managed_categories),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"{name} must not contain duplicate values.")


@dataclass(frozen=True, slots=True)
class ManagedCategoryV1:
    name: str
    path: Path

    def __post_init__(self) -> None:
        if self.name not in MANAGED_LOCAL_DATA_CATEGORIES:
            raise ValueError("Managed category name is not canonical.")
        if not isinstance(self.path, Path):
            raise ValueError("Managed category path must be a Path.")


@dataclass(frozen=True, slots=True)
class ManagedHomeV1:
    root: Path
    categories: tuple[ManagedCategoryV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise ValueError("Managed home root must be a Path.")
        categories = tuple(self.categories)
        object.__setattr__(self, "categories", categories)
        if any(type(category) is not ManagedCategoryV1 for category in categories):
            raise ValueError("Managed home categories must be exact managed categories.")
        if tuple(category.name for category in categories) != MANAGED_LOCAL_DATA_CATEGORIES:
            raise ValueError("Managed home categories must use canonical order.")
        if len(categories) != len(set(category.name for category in categories)):
            raise ValueError("Managed home categories must not repeat.")
        if any(category.path != self.root / category.name for category in categories):
            raise ValueError("Managed category paths must be direct managed-home children.")

    def category(self, name: str) -> ManagedCategoryV1:
        try:
            return next(category for category in self.categories if category.name == name)
        except StopIteration as error:
            raise KeyError(name) from error


@dataclass(frozen=True, slots=True)
class NavigationItemV1:
    route: str
    label: str

    def __post_init__(self) -> None:
        _require_text(self.route, "Navigation route")
        _require_text(self.label, "Navigation label")


@dataclass(frozen=True, slots=True)
class HomeTaskV1:
    route: str
    title: str
    description: str
    required_information: str
    storage: str
    mode: str
    expected_result: str
    available: bool
    availability: str

    def __post_init__(self) -> None:
        for name in (
            "route",
            "title",
            "description",
            "required_information",
            "storage",
            "mode",
            "expected_result",
            "availability",
        ):
            _require_text(getattr(self, name), f"Home task {name}")
        if type(self.available) is not bool:
            raise ValueError("Home task available must be a boolean.")


@dataclass(frozen=True, slots=True)
class BrowserSafeApplicationStateV1:
    product_name: str
    package_version: str
    python_runtime: str
    navigation: tuple[NavigationItemV1, ...]
    home_tasks: tuple[HomeTaskV1, ...]

    def __post_init__(self) -> None:
        for name in ("product_name", "package_version", "python_runtime"):
            _require_text(getattr(self, name), name)
        navigation = tuple(self.navigation)
        home_tasks = tuple(self.home_tasks)
        object.__setattr__(self, "navigation", navigation)
        object.__setattr__(self, "home_tasks", home_tasks)
        if any(type(item) is not NavigationItemV1 for item in navigation):
            raise ValueError("navigation must contain exact navigation items.")
        if any(type(item) is not HomeTaskV1 for item in home_tasks):
            raise ValueError("home_tasks must contain exact Home tasks.")
        if tuple(item.route for item in navigation) != APP_ROUTE_PATHS:
            raise ValueError("Navigation routes must use canonical order.")
        if tuple(item.label for item in navigation) != APP_NAVIGATION_LABELS:
            raise ValueError("Navigation labels must use canonical order.")
        if tuple(item.title for item in home_tasks) != APP_HOME_TASK_TITLES:
            raise ValueError("Home tasks must use canonical order.")
        if tuple(item.route for item in home_tasks) != APP_ROUTE_PATHS[1:]:
            raise ValueError("Home tasks must target the six canonical task routes.")
