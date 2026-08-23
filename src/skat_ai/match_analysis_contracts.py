from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from skat_ai.api.v1.contracts import (
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skat_ai.input_validation import MAX_SAMPLE_COUNT
from skat_ai.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_SKIP_REASONS,
    MatchDecisionOpponentProfileBindingV1,
)
from skat_ai.match_historical_materialization import (
    MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS,
)
from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.match_workspace_materialization import (
    MatchWorkspaceMaterializationV1,
    build_match_workspace_materialization_v1,
)
from skat_ai.recommendation_workflow import (
    FLAT_RECOMMENDATION_METHODS,
    FLAT_SEARCH_RECOMMENDATION_METHODS,
    IMMEDIATE_EXPECTED_VALUE_METHOD,
)
from skat_ai.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

MATCH_ANALYSIS_EXECUTION_VERSION = 1
MATCH_DECISION_ANALYSIS_OPTIONS_VERSION = 1
MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION = 1
MATCH_ANALYSIS_REPORT_VERSION = 1
MATCH_ANALYSIS_REPORT_STORE_VERSION = 1
MATCH_ARTIFACT_EXPORT_VERSION = 1

MATCH_ANALYSIS_OPERATIONS: Final[tuple[str, ...]] = (
    "prepare_materialization",
    "analyze_decision",
    "analyze_historical_game",
)
MATCH_ANALYSIS_EXECUTION_STATUSES: Final[tuple[str, ...]] = (
    "executed",
    "unavailable",
)
MATCH_DECISION_ANALYSIS_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "slot_not_observed_game",
    "decision_not_retained",
    "decision_not_preparable",
)
MATCH_ANALYSIS_REPORT_KINDS: Final[tuple[str, ...]] = (
    "materialization",
    "decision_analysis",
    "historical_analysis",
)
MATCH_ARTIFACT_EXPORT_KINDS: Final[tuple[str, ...]] = (
    "report_result",
    "materialization_summary",
    "historical_game_collection",
    "training_source_collection",
    "historical_list_input",
    "historical_list_aggregation",
)
MATCH_ANALYSIS_REPORT_STORE_LIMIT = 8

MATCH_ANALYSIS_EXECUTION_POLICY = "explicit_existing_application_execution_once"
MATCH_DECISION_ANALYSIS_INFORMATION_POLICY = "prepared_snapshot_plus_retrospective_actual_card"
MATCH_ANALYSIS_PROFILE_POLICY = "eligible_relative_profiles_via_existing_application"
MATCH_ANALYSIS_REPORT_POLICY = "ephemeral_revision_scoped_not_workspace_persisted"
MATCH_ANALYSIS_REPORT_ID_POLICY = "sha256_canonical_analysis_report_v1"
MATCH_ANALYSIS_EXPORT_POLICY = "authenticated_browser_download_without_server_path"
MATCH_ANALYSIS_AUTOMATION_POLICY = "never_execute_on_capture_mutation"

MATCH_ANALYSIS_SEARCH_BUDGET_PROFILES: Final[tuple[str, ...]] = (
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
)

_REPORT_ID_DOMAIN = b"skat-ai\0match_analysis_report_v1\0"


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_non_negative_integer(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


def _require_positive_integer(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def _require_sample_count(value: object, field_name: str) -> None:
    _require_positive_integer(value, field_name)
    if value > MAX_SAMPLE_COUNT:
        raise ValueError(f"{field_name} must be at most {MAX_SAMPLE_COUNT}.")


def _require_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchDecisionAnalysisOptionsV1:
    """Deterministic private options for one prepared Match Decision."""

    match_decision_analysis_options_version: int = MATCH_DECISION_ANALYSIS_OPTIONS_VERSION
    recommendation_method: str = IMMEDIATE_EXPECTED_VALUE_METHOD
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    immediate_random_seed: int = 0
    search_random_seed: int | None = None
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    use_profile_presets: bool = True

    def __post_init__(self) -> None:
        _require_version(
            self.match_decision_analysis_options_version,
            MATCH_DECISION_ANALYSIS_OPTIONS_VERSION,
            "match_decision_analysis_options_version",
        )
        if self.recommendation_method not in FLAT_RECOMMENDATION_METHODS:
            raise ValueError(
                f"recommendation_method must be one of {list(FLAT_RECOMMENDATION_METHODS)}."
            )
        _require_sample_count(self.immediate_sample_count, "immediate_sample_count")
        if type(self.immediate_random_seed) is not int:
            raise ValueError("immediate_random_seed must be an integer.")
        needs_search = self.recommendation_method in FLAT_SEARCH_RECOMMENDATION_METHODS
        if needs_search and type(self.search_random_seed) is not int:
            if self.recommendation_method == "information_set_search":
                raise ValueError("Information-set Search requires search_random_seed.")
            raise ValueError("Search and Auto require search_random_seed.")
        if not needs_search and self.search_random_seed is not None:
            raise ValueError("Immediate analysis requires search_random_seed to be null.")
        if self.search_budget_profile not in MATCH_ANALYSIS_SEARCH_BUDGET_PROFILES:
            raise ValueError(
                "search_budget_profile must be interactive_v1 or historical_review_v1."
            )
        if (
            not needs_search
            and self.search_budget_profile != HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
        ):
            raise ValueError("interactive_v1 requires a Search method.")
        if type(self.use_profile_presets) is not bool:
            raise ValueError("use_profile_presets must be a boolean.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_decision_analysis_options_version": (
                self.match_decision_analysis_options_version
            ),
            "recommendation_method": self.recommendation_method,
            "immediate_sample_count": self.immediate_sample_count,
            "immediate_random_seed": self.immediate_random_seed,
            "search_random_seed": self.search_random_seed,
            "search_budget_profile": self.search_budget_profile,
            "use_profile_presets": self.use_profile_presets,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchHistoricalAnalysisOptionsV1:
    """Deterministic private options for one strict Historical Match Game."""

    match_historical_analysis_options_version: int = MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION
    decision_snapshots: bool = False
    immediate_review: bool = True
    search_review: bool = False
    information_set_search_review: bool = False
    replay_coaching: bool = False
    information_set_replay_coaching: bool = False
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    immediate_random_seed: int = 0
    search_random_seed: int | None = None
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    use_profile_presets: bool = True

    def __post_init__(self) -> None:
        _require_version(
            self.match_historical_analysis_options_version,
            MATCH_HISTORICAL_ANALYSIS_OPTIONS_VERSION,
            "match_historical_analysis_options_version",
        )
        for field_name in (
            "decision_snapshots",
            "immediate_review",
            "search_review",
            "information_set_search_review",
            "replay_coaching",
            "information_set_replay_coaching",
            "use_profile_presets",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be a boolean.")
        if not (
            self.decision_snapshots
            or self.immediate_review
            or self.search_review
            or self.information_set_search_review
            or self.replay_coaching
            or self.information_set_replay_coaching
        ):
            raise ValueError("At least one Historical analysis mode must be selected.")
        existing_family = self.search_review or self.replay_coaching
        information_set_family = (
            self.information_set_search_review
            or self.information_set_replay_coaching
        )
        if existing_family and information_set_family:
            raise ValueError(
                "Existing and Information-set Historical Search/Coaching families "
                "cannot be combined."
            )
        _require_sample_count(self.immediate_sample_count, "immediate_sample_count")
        if type(self.immediate_random_seed) is not int:
            raise ValueError("immediate_random_seed must be an integer.")
        needs_search = existing_family or information_set_family
        if needs_search and type(self.search_random_seed) is not int:
            raise ValueError("Historical Search and Coaching require search_random_seed.")
        if not needs_search and self.search_random_seed is not None:
            raise ValueError("search_random_seed requires Historical Search or Coaching.")
        if self.search_budget_profile not in MATCH_ANALYSIS_SEARCH_BUDGET_PROFILES:
            raise ValueError(
                "search_budget_profile must be interactive_v1 or historical_review_v1."
            )
        if (
            not needs_search
            and self.search_budget_profile != HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
        ):
            raise ValueError("interactive_v1 requires Historical Search Review or Replay Coaching.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_historical_analysis_options_version": (
                self.match_historical_analysis_options_version
            ),
            "decision_snapshots": self.decision_snapshots,
            "immediate_review": self.immediate_review,
            "search_review": self.search_review,
            "information_set_search_review": self.information_set_search_review,
            "replay_coaching": self.replay_coaching,
            "information_set_replay_coaching": (
                self.information_set_replay_coaching
            ),
            "immediate_sample_count": self.immediate_sample_count,
            "immediate_random_seed": self.immediate_random_seed,
            "search_random_seed": self.search_random_seed,
            "search_budget_profile": self.search_budget_profile,
            "use_profile_presets": self.use_profile_presets,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchDecisionAnalysisResultV1:
    """Executed Position analysis or normal prepared-Decision unavailability."""

    match_analysis_execution_version: int = MATCH_ANALYSIS_EXECUTION_VERSION
    status: str
    match_id: str
    workspace_revision: int
    match_position: int
    game_id: str | None
    decision_index: int
    unavailable_reason: str | None
    skipped_reason: str | None
    options: MatchDecisionAnalysisOptionsV1
    profile_binding: MatchDecisionOpponentProfileBindingV1 | None
    request: RequestDocumentV1 | None
    result: ResultDocumentV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.match_analysis_execution_version,
            MATCH_ANALYSIS_EXECUTION_VERSION,
            "match_analysis_execution_version",
        )
        if self.status not in MATCH_ANALYSIS_EXECUTION_STATUSES:
            raise ValueError(f"status must be one of {list(MATCH_ANALYSIS_EXECUTION_STATUSES)}.")
        _require_identifier(self.match_id, "match_id")
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        _require_positive_integer(self.decision_index, "decision_index")
        if type(self.options) is not MatchDecisionAnalysisOptionsV1:
            raise ValueError("options must be MatchDecisionAnalysisOptionsV1.")
        if self.profile_binding is not None and type(self.profile_binding) is not (
            MatchDecisionOpponentProfileBindingV1
        ):
            raise ValueError(
                "profile_binding must be MatchDecisionOpponentProfileBindingV1 or null."
            )
        if self.status == "executed":
            if (
                self.game_id is None
                or self.unavailable_reason is not None
                or self.skipped_reason is not None
                or type(self.profile_binding) is not MatchDecisionOpponentProfileBindingV1
                or type(self.request) is not RequestDocumentV1
                or type(self.result) is not ResultDocumentV1
            ):
                raise ValueError("Executed Decision analysis requires request and result.")
            if (
                self.request.workflow is not WorkflowV1.POSITION_ANALYSIS
                or self.result.workflow is not WorkflowV1.POSITION_ANALYSIS
            ):
                raise ValueError("Executed Decision analysis must use position_analysis.")
            if self.profile_binding.decision_index != self.decision_index:
                raise ValueError("profile_binding must match decision_index.")
            request_document = self.request.document
            result_document = self.result.document
            expected_reference = (
                f"match:{self.match_id}:workspace:{self.workspace_revision}:"
                f"position:{self.match_position}:decision:{self.decision_index}"
            )
            if (
                request_document.get("analysis_mode") != "post_game_review"
                or request_document.get("actual_card_played") is None
                or request_document.get("game_end_reason") != "not_ended"
                or result_document.get("input_file") != expected_reference
            ):
                raise ValueError(
                    "Executed Decision request and result must retain source identity."
                )
            review = result_document.get("post_game_review_summary")
            if not isinstance(review, Mapping) or review.get(
                "actual_card_played"
            ) != request_document.get("actual_card_played"):
                raise ValueError(
                    "Executed Decision result must retain the retrospective actual Card."
                )
        else:
            if (
                self.unavailable_reason not in MATCH_DECISION_ANALYSIS_UNAVAILABLE_REASONS
                or self.request is not None
                or self.result is not None
                or self.profile_binding is not None
            ):
                raise ValueError("Unavailable Decision analysis requires one canonical reason.")
            if self.unavailable_reason == "slot_not_observed_game":
                if self.game_id is not None:
                    raise ValueError("A non-observed Slot cannot contain game_id.")
            elif self.game_id is None:
                raise ValueError("Observed-Game unavailability requires game_id.")
            if self.unavailable_reason == "decision_not_preparable":
                if self.skipped_reason not in MATCH_DECISION_REVIEW_SKIP_REASONS:
                    raise ValueError(
                        "decision_not_preparable requires one canonical skipped_reason."
                    )
            elif self.skipped_reason is not None:
                raise ValueError("skipped_reason is allowed only for decision_not_preparable.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_analysis_execution_version": self.match_analysis_execution_version,
            "status": self.status,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "unavailable_reason": self.unavailable_reason,
            "skipped_reason": self.skipped_reason,
            "options": self.options.to_dict(),
            "profile_binding": (
                None if self.profile_binding is None else self.profile_binding.to_dict()
            ),
            "request": None if self.request is None else self.request.to_dict(),
            "result": None if self.result is None else self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchHistoricalAnalysisResultV1:
    """Executed Historical analysis or mirrored strict materialization absence."""

    match_analysis_execution_version: int = MATCH_ANALYSIS_EXECUTION_VERSION
    status: str
    match_id: str
    workspace_revision: int
    match_position: int
    game_id: str | None
    unavailable_reason: str | None
    options: MatchHistoricalAnalysisOptionsV1
    request: RequestDocumentV1 | None
    result: ResultDocumentV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.match_analysis_execution_version,
            MATCH_ANALYSIS_EXECUTION_VERSION,
            "match_analysis_execution_version",
        )
        if self.status not in MATCH_ANALYSIS_EXECUTION_STATUSES:
            raise ValueError(f"status must be one of {list(MATCH_ANALYSIS_EXECUTION_STATUSES)}.")
        _require_identifier(self.match_id, "match_id")
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        if type(self.options) is not MatchHistoricalAnalysisOptionsV1:
            raise ValueError("options must be MatchHistoricalAnalysisOptionsV1.")
        if self.status == "executed":
            if (
                self.game_id is None
                or self.unavailable_reason is not None
                or type(self.request) is not RequestDocumentV1
                or type(self.result) is not ResultDocumentV1
            ):
                raise ValueError("Executed Historical analysis requires request and result.")
            if (
                self.request.workflow is not WorkflowV1.HISTORICAL_GAME
                or self.result.workflow is not WorkflowV1.HISTORICAL_GAME
            ):
                raise ValueError("Executed Historical analysis must use historical_game.")
            historical_input = self.request.document.get("historical_game_input")
            historical_summary = self.result.document.get("historical_game_summary")
            if (
                not isinstance(historical_input, Mapping)
                or historical_input.get("game_id") != self.game_id
                or not isinstance(historical_summary, Mapping)
                or historical_summary.get("game_id") != self.game_id
                or self.result.document.get("input_file")
                != (
                    f"match:{self.match_id}:workspace:{self.workspace_revision}:"
                    f"position:{self.match_position}:historical"
                )
            ):
                raise ValueError("Executed Historical request and result must retain game_id.")
        elif (
            self.unavailable_reason not in MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS
            or self.request is not None
            or self.result is not None
        ):
            raise ValueError("Unavailable Historical analysis requires one materialization reason.")
        elif self.unavailable_reason in {"slot_empty", "passed_deal"}:
            if self.game_id is not None:
                raise ValueError("A non-Game Historical result cannot contain game_id.")
        elif self.game_id is None:
            raise ValueError("Unavailable observed-Game Historical analysis requires game_id.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_analysis_execution_version": self.match_analysis_execution_version,
            "status": self.status,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "unavailable_reason": self.unavailable_reason,
            "options": self.options.to_dict(),
            "request": None if self.request is None else self.request.to_dict(),
            "result": None if self.result is None else self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchMaterializationReportV1:
    """One exact Match Workspace materialization prepared without execution."""

    match_id: str
    workspace_revision: int
    materialization: MatchWorkspaceMaterializationV1

    def __post_init__(self) -> None:
        _require_identifier(self.match_id, "match_id")
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if type(self.materialization) is not MatchWorkspaceMaterializationV1:
            raise ValueError("materialization must be MatchWorkspaceMaterializationV1.")
        if (
            self.materialization.match_id != self.match_id
            or self.materialization.workspace_revision != self.workspace_revision
        ):
            raise ValueError("materialization must retain report source identity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "materialization": self.materialization.to_dict(),
        }


MatchAnalysisReportValueV1 = (
    MatchMaterializationReportV1 | MatchDecisionAnalysisResultV1 | MatchHistoricalAnalysisResultV1
)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchAnalysisReportV1:
    """Revision-scoped private report with content-derived identity."""

    match_analysis_report_version: int = MATCH_ANALYSIS_REPORT_VERSION
    report_id: str = field(init=False)
    report_kind: str
    match_id: str
    workspace_revision: int
    match_position: int | None
    decision_index: int | None
    value: MatchAnalysisReportValueV1 = field(repr=False)

    def __post_init__(self) -> None:
        _require_version(
            self.match_analysis_report_version,
            MATCH_ANALYSIS_REPORT_VERSION,
            "match_analysis_report_version",
        )
        if self.report_kind not in MATCH_ANALYSIS_REPORT_KINDS:
            raise ValueError(f"report_kind must be one of {list(MATCH_ANALYSIS_REPORT_KINDS)}.")
        _require_identifier(self.match_id, "match_id")
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        expected_type = {
            "materialization": MatchMaterializationReportV1,
            "decision_analysis": MatchDecisionAnalysisResultV1,
            "historical_analysis": MatchHistoricalAnalysisResultV1,
        }[self.report_kind]
        if type(self.value) is not expected_type:
            raise ValueError("value type must match report_kind.")
        if (
            self.value.match_id != self.match_id
            or self.value.workspace_revision != self.workspace_revision
        ):
            raise ValueError("value must retain report source identity.")
        if self.report_kind == "materialization":
            if self.match_position is not None or self.decision_index is not None:
                raise ValueError("Materialization reports are Match-wide.")
        else:
            if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
                raise ValueError("Analysis reports require a Match position.")
            if self.value.match_position != self.match_position:
                raise ValueError("value must match report Match position.")
            if self.report_kind == "decision_analysis":
                if type(self.decision_index) is not int or self.decision_index <= 0:
                    raise ValueError("Decision reports require a positive decision_index.")
                if self.value.decision_index != self.decision_index:
                    raise ValueError("value must match report Decision index.")
            elif self.decision_index is not None:
                raise ValueError("decision_index is allowed only for Decision reports.")
        object.__setattr__(self, "report_id", self._build_report_id())

    def _identity_document(self) -> dict[str, Any]:
        return {
            "match_analysis_report_version": self.match_analysis_report_version,
            "report_kind": self.report_kind,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "decision_index": self.decision_index,
            "value": self.value.to_dict(),
        }

    def _build_report_id(self) -> str:
        return hashlib.sha256(
            _REPORT_ID_DOMAIN + _canonical_json_bytes(self._identity_document())
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        identity = self._identity_document()
        return {
            "match_analysis_report_version": identity["match_analysis_report_version"],
            "report_id": self.report_id,
            "report_kind": identity["report_kind"],
            "match_id": identity["match_id"],
            "workspace_revision": identity["workspace_revision"],
            "match_position": identity["match_position"],
            "decision_index": identity["decision_index"],
            "value": identity["value"],
        }


def prepare_match_materialization_report_v1(
    workspace: MatchWorkspaceV1,
    *,
    lot_order: tuple[str, ...] | None = None,
) -> MatchMaterializationReportV1:
    """Builds one complete materialization exactly once and executes no workflow."""
    materialization = build_match_workspace_materialization_v1(
        workspace,
        lot_order=lot_order,
    )
    return MatchMaterializationReportV1(
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        materialization=materialization,
    )


def build_match_analysis_report_v1(
    value: MatchAnalysisReportValueV1,
) -> MatchAnalysisReportV1:
    """Wraps one complete analysis value with its deterministic report identity."""
    if type(value) is MatchMaterializationReportV1:
        return MatchAnalysisReportV1(
            report_kind="materialization",
            match_id=value.match_id,
            workspace_revision=value.workspace_revision,
            match_position=None,
            decision_index=None,
            value=value,
        )
    if type(value) is MatchDecisionAnalysisResultV1:
        return MatchAnalysisReportV1(
            report_kind="decision_analysis",
            match_id=value.match_id,
            workspace_revision=value.workspace_revision,
            match_position=value.match_position,
            decision_index=value.decision_index,
            value=value,
        )
    if type(value) is MatchHistoricalAnalysisResultV1:
        return MatchAnalysisReportV1(
            report_kind="historical_analysis",
            match_id=value.match_id,
            workspace_revision=value.workspace_revision,
            match_position=value.match_position,
            decision_index=None,
            value=value,
        )
    raise ValueError("value must be one Match analysis report value.")
