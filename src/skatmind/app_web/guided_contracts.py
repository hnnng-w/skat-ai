from __future__ import annotations

GUIDED_ANALYSIS_FRONTEND_VERSION = 1
GUIDED_POSITION_FORM_VERSION = 1
GUIDED_HISTORICAL_REVIEW_FORM_VERSION = 1
FRONTEND_RESULT_PRESENTATION_VERSION = 1
FRONTEND_JSON_TRANSFER_VERSION = 1
PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION = 1

GUIDED_ANALYSIS_FRONTEND_POLICIES = (
    "guided_forms_build_existing_root_documents",
    "one_explicit_application_execution_per_run",
    "normal_forms_reuse_existing_product_defaults",
    "advanced_settings_are_collapsed_and_explained",
    "strict_json_import_is_explicit_and_non_executing",
    "exact_json_download_uses_retained_values",
    "public_result_is_the_only_presentation_source",
    "normal_result_states_are_not_transport_errors",
    "process_local_state_without_implicit_persistence",
    "private_engine_state_never_enters_browser_state",
)

ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH = "/actions/analyze/run-guided"
ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH = "/actions/analyze/import-json"
ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH = "/actions/analyze/run-imported"
ANALYZE_RESET_ACTION_ROUTE_PATH = "/actions/analyze/reset"

REVIEW_START_ACTION_ROUTE_PATH = "/actions/review/start"
REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH = "/actions/review/update-players"
REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH = "/actions/review/update-deal"
REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH = "/actions/review/update-declaration"
REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH = "/actions/review/update-discards"
REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH = "/actions/review/append-play"
REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH = "/actions/review/undo-play"
REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH = "/actions/review/update-options"
REVIEW_BACK_ACTION_ROUTE_PATH = "/actions/review/back"
REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH = "/actions/review/run-guided"
REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH = "/actions/review/import-json"
REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH = "/actions/review/run-imported"
REVIEW_RESET_ACTION_ROUTE_PATH = "/actions/review/reset"

ANALYZE_ACTION_ROUTE_PATHS = (
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    ANALYZE_RESET_ACTION_ROUTE_PATH,
)
REVIEW_ACTION_ROUTE_PATHS = (
    REVIEW_START_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_BACK_ACTION_ROUTE_PATH,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_RESET_ACTION_ROUTE_PATH,
)
GUIDED_ACTION_ROUTE_PATHS = ANALYZE_ACTION_ROUTE_PATHS + REVIEW_ACTION_ROUTE_PATHS

ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH = "/downloads/analyze/request.json"
ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH = "/downloads/analyze/result.json"
REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH = "/downloads/review/request.json"
REVIEW_RESULT_DOWNLOAD_ROUTE_PATH = "/downloads/review/result.json"
GUIDED_DOWNLOAD_ROUTE_PATHS = (
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
)

POSITION_REQUEST_DOWNLOAD_FILENAME = "skatmind-position-request.json"
POSITION_RESULT_DOWNLOAD_FILENAME = "skatmind-position-result.json"
REVIEW_REQUEST_DOWNLOAD_FILENAME = "skatmind-review-request.json"
REVIEW_RESULT_DOWNLOAD_FILENAME = "skatmind-review-result.json"
GUIDED_DOWNLOAD_FILENAMES = (
    POSITION_REQUEST_DOWNLOAD_FILENAME,
    POSITION_RESULT_DOWNLOAD_FILENAME,
    REVIEW_REQUEST_DOWNLOAD_FILENAME,
    REVIEW_RESULT_DOWNLOAD_FILENAME,
)


def _require_version(value: object, expected: int, name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{name} must be the strict integer {expected}.")


def _require_exact_ordered_values(
    value: object,
    expected: tuple[str, ...],
    name: str,
) -> None:
    if type(value) is not tuple or value != expected:
        raise ValueError(f"{name} must contain the exact canonical ordered values.")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicate values.")


def validate_guided_frontend_contract_v1(
    *,
    guided_analysis_frontend_version: object = GUIDED_ANALYSIS_FRONTEND_VERSION,
    guided_position_form_version: object = GUIDED_POSITION_FORM_VERSION,
    guided_historical_review_form_version: object = GUIDED_HISTORICAL_REVIEW_FORM_VERSION,
    frontend_result_presentation_version: object = FRONTEND_RESULT_PRESENTATION_VERSION,
    frontend_json_transfer_version: object = FRONTEND_JSON_TRANSFER_VERSION,
    process_local_workflow_state_version: object = (
        PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION
    ),
    policies: object = GUIDED_ANALYSIS_FRONTEND_POLICIES,
    analyze_action_routes: object = ANALYZE_ACTION_ROUTE_PATHS,
    review_action_routes: object = REVIEW_ACTION_ROUTE_PATHS,
    download_routes: object = GUIDED_DOWNLOAD_ROUTE_PATHS,
    download_filenames: object = GUIDED_DOWNLOAD_FILENAMES,
) -> None:
    """Rejects version, policy, route, and filename drift in the private contract."""

    for value, expected, name in (
        (
            guided_analysis_frontend_version,
            GUIDED_ANALYSIS_FRONTEND_VERSION,
            "guided_analysis_frontend_version",
        ),
        (
            guided_position_form_version,
            GUIDED_POSITION_FORM_VERSION,
            "guided_position_form_version",
        ),
        (
            guided_historical_review_form_version,
            GUIDED_HISTORICAL_REVIEW_FORM_VERSION,
            "guided_historical_review_form_version",
        ),
        (
            frontend_result_presentation_version,
            FRONTEND_RESULT_PRESENTATION_VERSION,
            "frontend_result_presentation_version",
        ),
        (
            frontend_json_transfer_version,
            FRONTEND_JSON_TRANSFER_VERSION,
            "frontend_json_transfer_version",
        ),
        (
            process_local_workflow_state_version,
            PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION,
            "process_local_workflow_state_version",
        ),
    ):
        _require_version(value, expected, name)

    for value, expected, name in (
        (policies, GUIDED_ANALYSIS_FRONTEND_POLICIES, "policies"),
        (analyze_action_routes, ANALYZE_ACTION_ROUTE_PATHS, "analyze_action_routes"),
        (review_action_routes, REVIEW_ACTION_ROUTE_PATHS, "review_action_routes"),
        (download_routes, GUIDED_DOWNLOAD_ROUTE_PATHS, "download_routes"),
        (download_filenames, GUIDED_DOWNLOAD_FILENAMES, "download_filenames"),
    ):
        _require_exact_ordered_values(value, expected, name)
