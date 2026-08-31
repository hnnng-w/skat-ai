from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path

import pytest

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.contracts import (
    APP_HOME_TASK_TITLES,
    APP_NAVIGATION_LABELS,
    APP_ROUTE_PATHS,
    LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION,
    MANAGED_LOCAL_DATA_CATEGORIES,
    MANAGED_LOCAL_DATA_CONTRACT_VERSION,
    UNIFIED_LOCAL_FRONTEND_CONTRACT_VERSION,
    UNIFIED_LOCAL_FRONTEND_POLICIES,
    BrowserSafeApplicationStateV1,
    HomeTaskV1,
    ManagedCategoryV1,
    ManagedHomeV1,
    NavigationItemV1,
    validate_unified_local_frontend_contract_v1,
)
from skatmind.app_web.managed_data import (
    prepare_managed_home_v1,
    resolve_managed_data_root_v1,
    resolve_platform_managed_data_root_v1,
)
from skatmind.app_web.rendering import render_app_page_v1
from skatmind.app_web.state import build_browser_safe_application_state_v1


def test_unified_local_frontend_contract_identity_and_policies_are_exact() -> None:
    assert UNIFIED_LOCAL_FRONTEND_CONTRACT_VERSION == 1
    assert LOCAL_FRONTEND_LAUNCH_CONTRACT_VERSION == 1
    assert MANAGED_LOCAL_DATA_CONTRACT_VERSION == 1
    assert UNIFIED_LOCAL_FRONTEND_POLICIES == (
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


def test_routes_navigation_home_tasks_and_categories_are_exact_and_ordered() -> None:
    assert APP_ROUTE_PATHS == (
        "/",
        "/analyze",
        "/review",
        "/sessions",
        "/matches",
        "/learning",
        "/about",
    )
    assert APP_NAVIGATION_LABELS == (
        "Home",
        "Analyze a position",
        "Review a completed game",
        "Sessions",
        "Match capture",
        "Learning & cross-game insights",
        "About SkatMind",
    )
    assert APP_HOME_TASK_TITLES == (
        "Analyze a position",
        "Review a completed game",
        "Create or resume a Session",
        "Capture a 36-game Match",
        "Open Learning & cross-game insights",
        "About SkatMind",
    )
    assert MANAGED_LOCAL_DATA_CATEGORIES == ("sessions", "matches", "corpora")
    validate_unified_local_frontend_contract_v1()


@pytest.mark.parametrize(
    ("name", "canonical"),
    (
        ("policies", UNIFIED_LOCAL_FRONTEND_POLICIES),
        ("routes", APP_ROUTE_PATHS),
        ("navigation_labels", APP_NAVIGATION_LABELS),
        ("home_tasks", APP_HOME_TASK_TITLES),
        ("managed_categories", MANAGED_LOCAL_DATA_CATEGORIES),
    ),
)
@pytest.mark.parametrize("mutation", ("reordered", "duplicated", "missing", "changed"))
def test_contract_validation_rejects_all_canonical_value_drift(
    name: str,
    canonical: tuple[str, ...],
    mutation: str,
) -> None:
    if mutation == "reordered":
        changed = (canonical[1], canonical[0], *canonical[2:])
    elif mutation == "duplicated":
        changed = (*canonical[:-1], canonical[0])
    elif mutation == "missing":
        changed = canonical[:-1]
    else:
        changed = (*canonical[:-1], "mutated")
    with pytest.raises(ValueError, match="exact canonical ordered values"):
        validate_unified_local_frontend_contract_v1(**{name: changed})


def test_windows_and_linux_managed_roots_are_exact() -> None:
    assert resolve_platform_managed_data_root_v1(
        platform_name="win32",
        environ={"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"},
    ) == Path(r"C:\Users\Example\AppData\Local") / "SkatMind"
    assert resolve_platform_managed_data_root_v1(
        platform_name="linux",
        environ={"XDG_DATA_HOME": "/var/data", "HOME": "/home/example"},
    ) == Path("/var/data/skatmind")
    assert resolve_platform_managed_data_root_v1(
        platform_name="linux",
        environ={"HOME": "/home/example"},
    ) == Path("/home/example/.local/share/skatmind")


def test_managed_root_resolution_rejects_missing_environment_and_platform() -> None:
    with pytest.raises(OSError, match="LOCALAPPDATA"):
        resolve_platform_managed_data_root_v1(platform_name="win32", environ={})
    with pytest.raises(OSError, match="HOME"):
        resolve_platform_managed_data_root_v1(platform_name="linux", environ={})
    with pytest.raises(OSError, match="Windows and Linux"):
        resolve_platform_managed_data_root_v1(platform_name="darwin", environ={})
    with pytest.raises(ValueError, match="must not be empty"):
        resolve_managed_data_root_v1("   ")


def test_prepare_managed_home_creates_only_categories_and_is_idempotent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "managed" / "skatmind"
    home = prepare_managed_home_v1(root)
    assert home.root == root
    assert tuple(category.name for category in home.categories) == (
        "sessions",
        "matches",
        "corpora",
    )
    assert tuple(category.path for category in home.categories) == tuple(
        root / name for name in MANAGED_LOCAL_DATA_CATEGORIES
    )
    assert sorted(path.name for path in root.iterdir()) == ["corpora", "matches", "sessions"]

    retained = root / "sessions" / "existing-session.data"
    retained.write_text("not inspected", encoding="utf-8")
    assert prepare_managed_home_v1(root) == home
    assert retained.read_text(encoding="utf-8") == "not inspected"
    assert not (root / "manifest.json").exists()


def test_prepare_managed_home_does_not_enumerate_or_parse_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "managed"

    def unexpected_access(*_args, **_kwargs):
        raise AssertionError("Managed-home preparation inspected directory contents.")

    for name in ("glob", "iterdir", "read_bytes", "read_text", "rglob"):
        monkeypatch.setattr(Path, name, unexpected_access)

    home = prepare_managed_home_v1(root)
    assert home.root == root
    assert all((root / name).is_dir() for name in MANAGED_LOCAL_DATA_CATEGORIES)


def test_prepare_managed_home_rejects_root_and_category_file_collisions(
    tmp_path: Path,
) -> None:
    root_file = tmp_path / "root-file"
    root_file.write_text("collision", encoding="utf-8")
    with pytest.raises(NotADirectoryError, match="Managed data root"):
        prepare_managed_home_v1(root_file)

    category_root = tmp_path / "category-root"
    category_root.mkdir()
    (category_root / "matches").write_text("collision", encoding="utf-8")
    with pytest.raises(NotADirectoryError, match="matches"):
        prepare_managed_home_v1(category_root)
    assert (category_root / "sessions").is_dir()
    assert not (category_root / "corpora").exists()


def test_managed_contracts_are_immutable_ordered_and_path_private(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "home")
    assert home.category("matches").path == home.root / "matches"
    with pytest.raises(KeyError):
        home.category("unknown")
    with pytest.raises(AttributeError):
        home.root = tmp_path  # type: ignore[misc]
    with pytest.raises(ValueError, match="canonical order"):
        ManagedHomeV1(root=home.root, categories=tuple(reversed(home.categories)))
    with pytest.raises(ValueError, match="canonical"):
        ManagedCategoryV1(name="other", path=home.root / "other")


def test_browser_state_is_immutable_canonical_and_contains_no_private_values() -> None:
    state = build_browser_safe_application_state_v1()
    assert type(state) is BrowserSafeApplicationStateV1
    assert tuple(item.route for item in state.navigation) == APP_ROUTE_PATHS
    assert tuple(item.label for item in state.navigation) == APP_NAVIGATION_LABELS
    assert tuple(task.title for task in state.home_tasks) == APP_HOME_TASK_TITLES
    assert tuple(task.available for task in state.home_tasks) == (
        True,
        True,
        True,
        True,
        True,
        True,
    )
    document = asdict(state)
    serialized = repr(document).lower()
    for forbidden in (
        "path",
        "port",
        "token",
        "cookie",
        "environment",
        "user_name",
        "machine_name",
        "cards",
        "fingerprint",
        "timestamp",
    ):
        assert forbidden not in serialized


def test_navigation_and_task_inputs_are_defensively_copied() -> None:
    original = build_browser_safe_application_state_v1()
    navigation = list(original.navigation)
    tasks = list(original.home_tasks)
    copied = BrowserSafeApplicationStateV1(
        product_name=original.product_name,
        package_version=original.package_version,
        python_runtime=original.python_runtime,
        navigation=navigation,  # type: ignore[arg-type]
        home_tasks=tasks,  # type: ignore[arg-type]
    )
    navigation.clear()
    tasks.clear()
    assert copied.navigation == original.navigation
    assert copied.home_tasks == original.home_tasks


def test_browser_state_rejects_reordered_navigation_and_tasks() -> None:
    original = build_browser_safe_application_state_v1()
    with pytest.raises(ValueError, match="Navigation routes"):
        BrowserSafeApplicationStateV1(
            product_name="SkatMind",
            package_version="0.17.0",
            python_runtime="CPython 3.13.0",
            navigation=tuple(reversed(original.navigation)),
            home_tasks=original.home_tasks,
        )
    with pytest.raises(ValueError, match="Home tasks"):
        BrowserSafeApplicationStateV1(
            product_name="SkatMind",
            package_version="0.17.0",
            python_runtime="CPython 3.13.0",
            navigation=original.navigation,
            home_tasks=tuple(reversed(original.home_tasks)),
        )


def test_context_retains_private_home_separately_from_browser_state(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "private-home")
    context = AppWebContextV1.create(home)
    assert context.managed_home is home
    assert str(home.root) not in repr(asdict(context.browser_state))
    assert context.lock.acquire(blocking=False)
    context.lock.release()


def test_rendering_escapes_storage_disclosure_and_rejects_path_on_other_pages() -> None:
    state = build_browser_safe_application_state_v1()
    private_path = Path("private/<unsafe&location>")
    about = render_app_page_v1(state, "/about", storage_root=private_path)
    assert escape(str(private_path), quote=True) in about
    assert str(private_path) not in about
    assert about.count(str(private_path)) == 0
    assert '<details class="storage-disclosure">' in about
    assert '<details class="storage-disclosure" open' not in about
    with pytest.raises(ValueError, match="only on About"):
        render_app_page_v1(state, "/", storage_root=private_path)


def test_contract_types_reject_noncanonical_nested_values() -> None:
    with pytest.raises(ValueError, match="Navigation route"):
        NavigationItemV1(route="", label="Home")
    with pytest.raises(ValueError, match="available"):
        HomeTaskV1(
            route="/about",
            title="About SkatMind",
            description="About",
            required_information="None",
            storage="None",
            mode="Reference",
            expected_result="Information",
            available=1,  # type: ignore[arg-type]
            availability="Available",
        )
