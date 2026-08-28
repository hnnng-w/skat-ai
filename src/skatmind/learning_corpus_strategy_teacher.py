from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, cast

from skatmind.api.v1.contracts import (
    RequestDocumentV1,
    ResultDocumentV1,
    _freeze_json_object,
    _freeze_json_value,
    _thaw_json_value,
)
from skatmind.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skatmind.learning_corpus_information_set_strategy_teacher import (
    LearningCorpusInformationSetStrategyTeacherEvidenceV1,
)
from skatmind.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    _validate_match_analysis_report_identity_v1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_review_preparation import (
    MatchDecisionOpponentProfileBindingV1,
)
from skatmind.recommendation_workflow import FLAT_RECOMMENDATION_METHODS

LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION = 1
LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION = 1
LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION = 1

LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_REPORT_KINDS: Final[tuple[str, ...]] = (
    "decision_analysis",
)
LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES: Final[tuple[str, ...]] = (
    "recommendation_available",
    "recommendation_unavailable",
)
LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES: Final[tuple[str, ...]] = (
    "not_attempted",
    "complete",
    "partial",
    "timeout",
    "unavailable",
)

LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_POLICY = (
    "explicit_current_match_snapshot_bound_decision_reports"
)
LEARNING_CORPUS_STRATEGY_TEACHER_REPORT_POLICY = "exact_executed_decision_analysis_reports_only"
LEARNING_CORPUS_STRATEGY_TEACHER_RECONCILIATION_POLICY = (
    "rebuild_request_without_analysis_execution"
)
LEARNING_CORPUS_STRATEGY_TEACHER_CLAIM_POLICY = "method_bound_evidence_not_ground_truth"
LEARNING_CORPUS_STRATEGY_TEACHER_ACTUAL_CARD_POLICY = (
    "retrospective_observed_behavior_not_optimal_label"
)
LEARNING_CORPUS_STRATEGY_TEACHER_METHOD_POLICY = (
    "preserve_existing_method_budget_status_and_candidate_semantics"
)
LEARNING_CORPUS_STRATEGY_TEACHER_MULTIPLE_REPORT_POLICY = (
    "retain_distinct_reports_without_preferred_teacher"
)
LEARNING_CORPUS_STRATEGY_TEACHER_SEMANTIC_ID_POLICY = "exclude_wall_clock_elapsed_time_only"
LEARNING_CORPUS_STRATEGY_TEACHER_PROFILE_POLICY = (
    "retain_existing_binding_and_application_context_without_rederivation"
)
LEARNING_CORPUS_STRATEGY_TEACHER_EXECUTION_POLICY = "no_analysis_execution_or_rerun"
LEARNING_CORPUS_STRATEGY_TEACHER_PRIVACY_POLICY = (
    "private_local_minimized_unredacted_strategy_evidence"
)
LEARNING_CORPUS_STRATEGY_TEACHER_EXPORT_POLICY = "deterministic_path_free_json_document"
LEARNING_CORPUS_STRATEGY_TEACHER_DATASET_POLICY = "no_training_dataset_version_1_influence"

_REPORT_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_report_v1\0"
_REQUEST_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_request_v1\0"
_RESULT_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_result_v1\0"
_SOURCE_BINDING_ID_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_source_binding_v1\0"
_SEMANTIC_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_semantic_v1\0"
_EVIDENCE_ID_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_evidence_v1\0"
_COLLECTION_FINGERPRINT_DOMAIN = b"skatmind\0learning_corpus_strategy_teacher_collection_v1\0"

_EVIDENCE_MAPPING_FIELDS = (
    "settings",
    "analysis_metadata",
    "information_policy_summary",
    "opponent_policy_settings",
    "left_opponent_policy_settings",
    "right_opponent_policy_settings",
    "profile_preset_settings",
    "opponent_profile_application_summary",
    "recommendation_method_summary",
    "recommendation",
    "bounded_search_result",
    "post_game_review_summary",
    "bounded_search_post_game_review_summary",
    "requested_budget",
    "consumed_budget",
)
_EVIDENCE_SEQUENCE_FIELDS = (
    "legal_cards",
    "immediate_candidate_results",
    "search_candidate_results",
)
_SEMANTIC_SOURCE_IDENTITY_FIELDS = {
    "strategy_teacher_evidence_id",
    "teacher_semantic_fingerprint",
    "source_binding_id",
    "source_report_id",
    "source_report_fingerprint",
    "source_request_fingerprint",
    "source_result_fingerprint",
}
_METHOD_ORDER = {method: index for index, method in enumerate(FLAT_RECOMMENDATION_METHODS)}


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_hash_tuple(value: tuple[str, ...], field_name: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        _require_hash(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique IDs.")


def _freeze_mapping(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> Mapping[str, object] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, Mapping):
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a JSON object{nullable}.")
    return _freeze_json_object(
        cast(Mapping[str, object], _canonicalize_json_mapping_order(value)),
        path=field_name,
    )


def _freeze_sequence(value: object, field_name: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be an ordered JSON array.")
    frozen = _freeze_json_value(
        _canonicalize_json_mapping_order(value),
        path=field_name,
    )
    if type(frozen) is not tuple:
        raise ValueError(f"{field_name} must be an ordered JSON array.")
    return frozen


def _json_value(value: object) -> Any:
    if type(value) is MatchDecisionAnalysisOptionsV1:
        return value.to_dict()
    if type(value) is MatchDecisionOpponentProfileBindingV1:
        return value.to_dict()
    if type(value) is LearningCorpusInformationSetStrategyTeacherEvidenceV1:
        return value.to_dict()
    return _thaw_json_value(value)


def _canonicalize_json_mapping_order(value: object) -> object:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings.")
        return {
            key: _canonicalize_json_mapping_order(value[key])
            for key in sorted(cast(Mapping[str, object], value))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonicalize_json_mapping_order(item) for item in value]
    return value


def _strictly_rebuild_decision_report(
    report: MatchAnalysisReportV1,
) -> MatchAnalysisReportV1:
    value = cast(MatchDecisionAnalysisResultV1, report.value)
    options = MatchDecisionAnalysisOptionsV1(**value.options.to_dict())
    binding = cast(MatchDecisionOpponentProfileBindingV1, value.profile_binding)
    rebuilt_binding = MatchDecisionOpponentProfileBindingV1(**binding.to_dict())
    request = cast(RequestDocumentV1, value.request)
    request_document = request.to_dict()
    rebuilt_request = RequestDocumentV1(
        api_contract_version=request.api_contract_version,
        workflow=request.workflow,
        document=request_document["document"],
    )
    result = cast(ResultDocumentV1, value.result)
    result_document = result.to_dict()
    rebuilt_result = ResultDocumentV1(
        api_contract_version=result.api_contract_version,
        workflow=result.workflow,
        document=result_document["document"],
        warnings=result.warnings,
    )
    rebuilt_value = MatchDecisionAnalysisResultV1(
        match_analysis_execution_version=value.match_analysis_execution_version,
        status=value.status,
        match_id=value.match_id,
        workspace_revision=value.workspace_revision,
        match_position=value.match_position,
        game_id=value.game_id,
        decision_index=value.decision_index,
        unavailable_reason=value.unavailable_reason,
        skipped_reason=value.skipped_reason,
        options=options,
        profile_binding=rebuilt_binding,
        request=rebuilt_request,
        result=rebuilt_result,
    )
    if rebuilt_value != value:
        raise ValueError("Source Decision Report must equal its strict nested reconstruction.")
    rebuilt = build_match_analysis_report_v1(rebuilt_value)
    if rebuilt._identity_document() != report._identity_document():
        raise ValueError("Source Decision Report must retain exact Report identity material.")
    _validate_match_analysis_report_identity_v1(report)
    return report


def _validate_exact_decision_report(report: MatchAnalysisReportV1) -> None:
    if type(report) is not MatchAnalysisReportV1:
        raise ValueError("report must be an exact MatchAnalysisReportV1.")
    if report.report_kind not in LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_REPORT_KINDS:
        raise ValueError("Strategy Teacher sources require decision_analysis reports.")
    if type(report.value) is not MatchDecisionAnalysisResultV1:
        raise ValueError("Strategy Teacher sources require a Decision Analysis value.")
    if report.value.status != "executed":
        raise ValueError("Strategy Teacher sources require an executed Decision Report.")
    if (
        type(report.value.options) is not MatchDecisionAnalysisOptionsV1
        or type(report.value.profile_binding) is not MatchDecisionOpponentProfileBindingV1
        or type(report.value.request) is not RequestDocumentV1
        or type(report.value.result) is not ResultDocumentV1
    ):
        raise ValueError(
            "Executed Decision Reports require exact options, binding, Request, and Result."
        )
    if _strictly_rebuild_decision_report(report) != report:
        raise ValueError("Source Report must equal its canonical Match Analysis Report.")


def build_learning_corpus_strategy_teacher_report_fingerprint_v1(
    report: MatchAnalysisReportV1,
) -> str:
    """Fingerprints one complete exact Match Analysis Report without execution."""
    if type(report) is not MatchAnalysisReportV1:
        raise ValueError("report must be an exact MatchAnalysisReportV1.")
    return _build_identifier(_REPORT_FINGERPRINT_DOMAIN, report.to_dict())


def build_learning_corpus_strategy_teacher_request_fingerprint_v1(
    request: RequestDocumentV1,
) -> str:
    """Fingerprints one complete immutable Position Request wrapper."""
    if type(request) is not RequestDocumentV1:
        raise ValueError("request must be an exact RequestDocumentV1.")
    return _build_identifier(_REQUEST_FINGERPRINT_DOMAIN, request.to_dict())


def build_learning_corpus_strategy_teacher_result_fingerprint_v1(
    result: ResultDocumentV1,
) -> str:
    """Fingerprints one complete immutable Position Result wrapper."""
    if type(result) is not ResultDocumentV1:
        raise ValueError("result must be an exact ResultDocumentV1.")
    return _build_identifier(_RESULT_FINGERPRINT_DOMAIN, result.to_dict())


def _source_binding_material_v1(
    *,
    match_snapshot_id: str,
    source_report_id: str,
    source_report_fingerprint: str,
    source_request_fingerprint: str,
    source_result_fingerprint: str,
) -> dict[str, object]:
    return {
        "learning_corpus_strategy_teacher_source_version": (
            LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION
        ),
        "match_snapshot_id": match_snapshot_id,
        "source_report_id": source_report_id,
        "source_report_fingerprint": source_report_fingerprint,
        "source_request_fingerprint": source_request_fingerprint,
        "source_result_fingerprint": source_result_fingerprint,
    }


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningCorpusStrategyTeacherReportSourceV1:
    """One exact executed Decision Report bound to one explicit Match Snapshot."""

    learning_corpus_strategy_teacher_source_version: int = (
        LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION
    )
    source_binding_id: str = field(init=False)
    match_snapshot_id: str
    source_report_id: str = field(init=False)
    source_report_fingerprint: str = field(init=False)
    source_request_fingerprint: str = field(init=False)
    source_result_fingerprint: str = field(init=False)
    report: MatchAnalysisReportV1 = field(repr=False)

    def __post_init__(self) -> None:
        _require_version(
            self.learning_corpus_strategy_teacher_source_version,
            LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION,
            "learning_corpus_strategy_teacher_source_version",
        )
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _validate_exact_decision_report(self.report)
        request = cast(MatchDecisionAnalysisResultV1, self.report.value).request
        result = cast(MatchDecisionAnalysisResultV1, self.report.value).result
        if type(request) is not RequestDocumentV1 or type(result) is not ResultDocumentV1:
            raise ValueError("Executed Decision Reports require an exact Request and Result.")
        source_report_fingerprint = build_learning_corpus_strategy_teacher_report_fingerprint_v1(
            self.report
        )
        source_request_fingerprint = build_learning_corpus_strategy_teacher_request_fingerprint_v1(
            request
        )
        source_result_fingerprint = build_learning_corpus_strategy_teacher_result_fingerprint_v1(
            result
        )
        source_report_id = self.report.report_id
        source_binding_id = _build_identifier(
            _SOURCE_BINDING_ID_DOMAIN,
            _source_binding_material_v1(
                match_snapshot_id=self.match_snapshot_id,
                source_report_id=source_report_id,
                source_report_fingerprint=source_report_fingerprint,
                source_request_fingerprint=source_request_fingerprint,
                source_result_fingerprint=source_result_fingerprint,
            ),
        )
        object.__setattr__(self, "source_binding_id", source_binding_id)
        object.__setattr__(self, "source_report_id", source_report_id)
        object.__setattr__(
            self,
            "source_report_fingerprint",
            source_report_fingerprint,
        )
        object.__setattr__(
            self,
            "source_request_fingerprint",
            source_request_fingerprint,
        )
        object.__setattr__(
            self,
            "source_result_fingerprint",
            source_result_fingerprint,
        )

    def _validate(self, *, verify_identities: bool, validate_report: bool) -> None:
        _require_version(
            self.learning_corpus_strategy_teacher_source_version,
            LEARNING_CORPUS_STRATEGY_TEACHER_SOURCE_VERSION,
            "learning_corpus_strategy_teacher_source_version",
        )
        for field_name in (
            "source_binding_id",
            "match_snapshot_id",
            "source_report_id",
            "source_report_fingerprint",
            "source_request_fingerprint",
            "source_result_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        if validate_report:
            _validate_exact_decision_report(self.report)
        elif type(self.report) is not MatchAnalysisReportV1:
            raise ValueError("report must be an exact MatchAnalysisReportV1.")
        value = self.report.value
        if type(value) is not MatchDecisionAnalysisResultV1:
            raise ValueError("Strategy Teacher sources require a Decision Analysis value.")
        if self.source_report_id != self.report.report_id:
            raise ValueError("source_report_id must equal the exact Report ID.")
        if verify_identities:
            request = value.request
            result = value.result
            if type(request) is not RequestDocumentV1 or type(result) is not ResultDocumentV1:
                raise ValueError("Executed Decision Reports require an exact Request and Result.")
            report_fingerprint = build_learning_corpus_strategy_teacher_report_fingerprint_v1(
                self.report
            )
            request_fingerprint = build_learning_corpus_strategy_teacher_request_fingerprint_v1(
                request
            )
            result_fingerprint = build_learning_corpus_strategy_teacher_result_fingerprint_v1(
                result
            )
            if (
                self.source_report_fingerprint != report_fingerprint
                or self.source_request_fingerprint != request_fingerprint
                or self.source_result_fingerprint != result_fingerprint
            ):
                raise ValueError("Report Source fingerprints must cover exact source values.")
            expected_binding = _build_identifier(
                _SOURCE_BINDING_ID_DOMAIN,
                _source_binding_material_v1(
                    match_snapshot_id=self.match_snapshot_id,
                    source_report_id=self.source_report_id,
                    source_report_fingerprint=self.source_report_fingerprint,
                    source_request_fingerprint=self.source_request_fingerprint,
                    source_result_fingerprint=self.source_result_fingerprint,
                ),
            )
            if self.source_binding_id != expected_binding:
                raise ValueError("source_binding_id must cover the exact source binding.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_strategy_teacher_source_version": (
                self.learning_corpus_strategy_teacher_source_version
            ),
            "source_binding_id": self.source_binding_id,
            "match_snapshot_id": self.match_snapshot_id,
            "source_report_id": self.source_report_id,
            "source_report_fingerprint": self.source_report_fingerprint,
            "source_request_fingerprint": self.source_request_fingerprint,
            "source_result_fingerprint": self.source_result_fingerprint,
            "report": self.report.to_dict(),
        }


def build_learning_corpus_strategy_teacher_report_source_v1(
    *,
    match_snapshot_id: str,
    report: MatchAnalysisReportV1,
) -> LearningCorpusStrategyTeacherReportSourceV1:
    """Binds one exact executed Decision Report to a caller-selected Snapshot."""
    return LearningCorpusStrategyTeacherReportSourceV1(
        match_snapshot_id=match_snapshot_id,
        report=report,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusStrategyTeacherEvidenceV1:
    """Minimized method-bound strategy evidence for one observed Decision."""

    learning_corpus_strategy_teacher_evidence_version: int = (
        LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION
    )
    strategy_teacher_evidence_id: str
    teacher_semantic_fingerprint: str
    source_binding_id: str
    source_report_id: str
    source_report_fingerprint: str
    source_request_fingerprint: str
    source_result_fingerprint: str
    match_snapshot_id: str
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    workspace_revision: int
    match_position: int
    game_id: str
    decision_index: int
    acting_player_id: str
    actual_card_played: str
    status: str
    options: MatchDecisionAnalysisOptionsV1
    profile_binding: MatchDecisionOpponentProfileBindingV1
    settings: Mapping[str, object]
    analysis_metadata: Mapping[str, object]
    information_policy_summary: Mapping[str, object]
    legal_cards: tuple[object, ...]
    opponent_policy_settings: Mapping[str, object]
    left_opponent_policy_settings: Mapping[str, object]
    right_opponent_policy_settings: Mapping[str, object]
    profile_preset_settings: Mapping[str, object]
    opponent_profile_application_summary: Mapping[str, object] | None
    recommendation_method_summary: Mapping[str, object]
    recommendation: Mapping[str, object]
    strategic_summary: str
    immediate_candidate_results: tuple[object, ...]
    bounded_search_result: Mapping[str, object] | None
    information_set_search_evidence: LearningCorpusInformationSetStrategyTeacherEvidenceV1 | None
    post_game_review_summary: Mapping[str, object]
    bounded_search_post_game_review_summary: Mapping[str, object] | None
    search_status: str
    search_stop_reason: str | None
    world_coverage: str | None
    solution_claim: str | None
    policy_claim: str | None
    policy_consistency: str | None
    information_sets_evaluated: int | None
    controlled_policy_decision_count: int | None
    requested_budget: Mapping[str, object] | None
    consumed_budget: Mapping[str, object] | None
    search_candidate_results: tuple[object, ...]
    wall_clock_elapsed_ms: int | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusStrategyTeacherEvidenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusStrategyTeacherEvidenceV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_strategy_teacher_evidence_version",
            LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in _EVIDENCE_MAPPING_FIELDS:
                field_value = _freeze_mapping(
                    field_value,
                    field_name,
                    allow_none=field_name
                    in {
                        "opponent_profile_application_summary",
                        "bounded_search_result",
                        "bounded_search_post_game_review_summary",
                        "requested_budget",
                        "consumed_budget",
                    },
                )
            elif field_name in _EVIDENCE_SEQUENCE_FIELDS:
                field_value = _freeze_sequence(field_value, field_name)
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identities=False)
        return value

    def _validate(self, *, verify_identities: bool) -> None:
        _require_version(
            self.learning_corpus_strategy_teacher_evidence_version,
            LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION,
            "learning_corpus_strategy_teacher_evidence_version",
        )
        for field_name in (
            "strategy_teacher_evidence_id",
            "teacher_semantic_fingerprint",
            "source_binding_id",
            "source_report_id",
            "source_report_fingerprint",
            "source_request_fingerprint",
            "source_result_fingerprint",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        _require_positive_integer(self.decision_index, "decision_index")
        _require_identifier(self.actual_card_played, "actual_card_played")
        if self.status not in LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES:
            raise ValueError("status must be a canonical Strategy Teacher status.")
        if type(self.options) is not MatchDecisionAnalysisOptionsV1:
            raise ValueError("options must be an exact MatchDecisionAnalysisOptionsV1.")
        if type(self.profile_binding) is not MatchDecisionOpponentProfileBindingV1:
            raise ValueError(
                "profile_binding must be an exact MatchDecisionOpponentProfileBindingV1."
            )
        if (
            self.profile_binding.decision_index != self.decision_index
            or self.profile_binding.acting_player_id != self.acting_player_id
        ):
            raise ValueError("Profile binding must reconcile with the acting Decision.")
        for field_name in _EVIDENCE_MAPPING_FIELDS:
            field_value = getattr(self, field_name)
            if field_value is None and field_name in {
                "opponent_profile_application_summary",
                "bounded_search_result",
                "bounded_search_post_game_review_summary",
                "requested_budget",
                "consumed_budget",
            }:
                continue
            if not isinstance(field_value, Mapping):
                raise ValueError(f"{field_name} must retain an immutable JSON object.")
        for field_name in _EVIDENCE_SEQUENCE_FIELDS:
            if type(getattr(self, field_name)) is not tuple:
                raise ValueError(f"{field_name} must retain an immutable JSON array.")
        if (
            self.information_set_search_evidence is not None
            and type(self.information_set_search_evidence)
            is not LearningCorpusInformationSetStrategyTeacherEvidenceV1
        ):
            raise ValueError(
                "information_set_search_evidence must be an exact focused value or null."
            )
        if not isinstance(self.strategic_summary, str):
            raise ValueError("strategic_summary must be a string.")
        if self.actual_card_played not in self.legal_cards:
            raise ValueError("actual_card_played must be one retained legal Card.")

        requested_method = self.recommendation_method_summary.get("requested_method")
        effective_method = self.recommendation_method_summary.get("effective_method")
        search_attempted = self.recommendation_method_summary.get("search_attempted")
        fallback_used = self.recommendation_method_summary.get("fallback_used")
        if requested_method != self.options.recommendation_method:
            raise ValueError("Requested method must equal the exact source options.")
        if self.settings.get("recommendation_method") != requested_method:
            raise ValueError("Settings and method summary must use the same method.")
        if self.profile_preset_settings.get("use_profile_presets") != (
            self.options.use_profile_presets
        ):
            raise ValueError("Profile-Preset settings must equal the exact source options.")
        recommended_card = self.recommendation.get("card")
        expected_status = (
            LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES[0]
            if recommended_card is not None and effective_method != "none"
            else LEARNING_CORPUS_STRATEGY_TEACHER_STATUSES[1]
        )
        if self.status != expected_status:
            raise ValueError("Teacher status must match recommendation availability.")
        if self.post_game_review_summary.get("actual_card_played") != (self.actual_card_played):
            raise ValueError("Post-game review must retain the observed actual Card.")

        if search_attempted is False:
            if self.search_status != "not_attempted":
                raise ValueError("Non-Search evidence must use search_status not_attempted.")
            if self.bounded_search_result is not None:
                raise ValueError("Non-Search evidence cannot contain bounded Search.")
            if self.bounded_search_post_game_review_summary is not None:
                raise ValueError("Non-Search evidence cannot contain Search comparison.")
            if self.information_set_search_evidence is not None:
                raise ValueError("Non-Search evidence cannot contain Information-set Search.")
            if (
                any(
                    value is not None
                    for value in (
                        self.search_stop_reason,
                        self.world_coverage,
                        self.solution_claim,
                        self.policy_claim,
                        self.policy_consistency,
                        self.information_sets_evaluated,
                        self.controlled_policy_decision_count,
                        self.requested_budget,
                        self.consumed_budget,
                        self.wall_clock_elapsed_ms,
                    )
                )
                or self.search_candidate_results
            ):
                raise ValueError("Non-Search convenience fields must be null or empty.")
        elif search_attempted is True:
            if self.search_status not in LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES[1:]:
                raise ValueError("Attempted Search must retain an existing Search status.")
            if requested_method == "information_set_search":
                focused = self.information_set_search_evidence
                if focused is None:
                    raise ValueError("Information-set Search requires focused Teacher evidence.")
                if (
                    self.bounded_search_result is not None
                    or self.bounded_search_post_game_review_summary is not None
                    or self.solution_claim is not None
                    or fallback_used is not False
                ):
                    raise ValueError(
                        "Information-set Search cannot contain bounded Search or fallback."
                    )
                if (
                    self.search_status != focused.search_status
                    or self.search_stop_reason != focused.search_stop_reason
                    or self.world_coverage != focused.world_coverage
                    or self.policy_claim != focused.policy_claim
                    or self.policy_consistency != focused.policy_consistency
                    or self.information_sets_evaluated != focused.information_sets_evaluated
                    or self.controlled_policy_decision_count
                    != focused.controlled_policy_decision_count
                    or self.requested_budget != focused.requested_budget
                    or self.consumed_budget != focused.consumed_budget
                    or self.search_candidate_results != focused.candidate_results
                    or self.wall_clock_elapsed_ms != focused.wall_clock_elapsed_ms
                ):
                    raise ValueError(
                        "Search convenience fields must equal Information-set evidence."
                    )
            else:
                if self.information_set_search_evidence is not None:
                    raise ValueError("Bounded Search cannot contain Information-set evidence.")
                if any(
                    value is not None
                    for value in (
                        self.policy_claim,
                        self.policy_consistency,
                        self.information_sets_evaluated,
                        self.controlled_policy_decision_count,
                    )
                ):
                    raise ValueError(
                        "Bounded Search cannot contain Information-set convenience fields."
                    )
                search = self.bounded_search_result
                if search is None:
                    raise ValueError("Attempted Search requires bounded_search_result.")
                if self.bounded_search_post_game_review_summary is None:
                    raise ValueError("Attempted post-game Search requires its comparisons.")
                expected_consumed = search.get("consumed_budget")
                if not isinstance(expected_consumed, Mapping):
                    raise ValueError("Bounded Search must retain consumed_budget.")
                if (
                    self.search_status != search.get("status")
                    or self.search_stop_reason != search.get("stop_reason")
                    or self.world_coverage != search.get("world_coverage")
                    or self.solution_claim != search.get("solution_claim")
                    or self.requested_budget != search.get("requested_budget")
                    or self.consumed_budget != expected_consumed
                    or self.search_candidate_results
                    != tuple(cast(Sequence[object], search.get("candidate_results")))
                    or self.wall_clock_elapsed_ms != expected_consumed.get("wall_clock_elapsed_ms")
                ):
                    raise ValueError("Search convenience fields must equal bounded Search.")
                if fallback_used != search.get("fallback_used"):
                    raise ValueError("Search and method fallback state must reconcile.")
        else:
            raise ValueError("search_attempted must be a boolean.")
        if type(fallback_used) is not bool:
            raise ValueError("fallback_used must be a boolean.")

        if verify_identities:
            expected_binding = _build_identifier(
                _SOURCE_BINDING_ID_DOMAIN,
                _source_binding_material_v1(
                    match_snapshot_id=self.match_snapshot_id,
                    source_report_id=self.source_report_id,
                    source_report_fingerprint=self.source_report_fingerprint,
                    source_request_fingerprint=self.source_request_fingerprint,
                    source_result_fingerprint=self.source_result_fingerprint,
                ),
            )
            if self.source_binding_id != expected_binding:
                raise ValueError("Evidence source binding identity must reconcile.")
            expected_semantic = _build_identifier(
                _SEMANTIC_FINGERPRINT_DOMAIN,
                _teacher_semantic_material_v1(self.to_dict()),
            )
            if self.teacher_semantic_fingerprint != expected_semantic:
                raise ValueError("teacher_semantic_fingerprint must cover exact semantic evidence.")
            expected_evidence_id = _build_identifier(
                _EVIDENCE_ID_DOMAIN,
                _evidence_identity_material_v1(self.to_dict()),
            )
            if self.strategy_teacher_evidence_id != expected_evidence_id:
                raise ValueError("strategy_teacher_evidence_id must cover exact source evidence.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_strategy_teacher_evidence_version": (
                self.learning_corpus_strategy_teacher_evidence_version
            ),
            "strategy_teacher_evidence_id": self.strategy_teacher_evidence_id,
            "teacher_semantic_fingerprint": self.teacher_semantic_fingerprint,
            "source_binding_id": self.source_binding_id,
            "source_report_id": self.source_report_id,
            "source_report_fingerprint": self.source_report_fingerprint,
            "source_request_fingerprint": self.source_request_fingerprint,
            "source_result_fingerprint": self.source_result_fingerprint,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "decision_reference_id": self.decision_reference_id,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "actual_card_played": self.actual_card_played,
            "status": self.status,
            "options": self.options.to_dict(),
            "profile_binding": self.profile_binding.to_dict(),
            "settings": _json_value(self.settings),
            "analysis_metadata": _json_value(self.analysis_metadata),
            "information_policy_summary": _json_value(self.information_policy_summary),
            "legal_cards": _json_value(self.legal_cards),
            "opponent_policy_settings": _json_value(self.opponent_policy_settings),
            "left_opponent_policy_settings": _json_value(self.left_opponent_policy_settings),
            "right_opponent_policy_settings": _json_value(self.right_opponent_policy_settings),
            "profile_preset_settings": _json_value(self.profile_preset_settings),
            "opponent_profile_application_summary": _json_value(
                self.opponent_profile_application_summary
            ),
            "recommendation_method_summary": _json_value(self.recommendation_method_summary),
            "recommendation": _json_value(self.recommendation),
            "strategic_summary": self.strategic_summary,
            "immediate_candidate_results": _json_value(self.immediate_candidate_results),
            "bounded_search_result": _json_value(self.bounded_search_result),
            "information_set_search_evidence": (
                None
                if self.information_set_search_evidence is None
                else self.information_set_search_evidence.to_dict()
            ),
            "post_game_review_summary": _json_value(self.post_game_review_summary),
            "bounded_search_post_game_review_summary": _json_value(
                self.bounded_search_post_game_review_summary
            ),
            "search_status": self.search_status,
            "search_stop_reason": self.search_stop_reason,
            "world_coverage": self.world_coverage,
            "solution_claim": self.solution_claim,
            "policy_claim": self.policy_claim,
            "policy_consistency": self.policy_consistency,
            "information_sets_evaluated": self.information_sets_evaluated,
            "controlled_policy_decision_count": (self.controlled_policy_decision_count),
            "requested_budget": _json_value(self.requested_budget),
            "consumed_budget": _json_value(self.consumed_budget),
            "search_candidate_results": _json_value(self.search_candidate_results),
            "wall_clock_elapsed_ms": self.wall_clock_elapsed_ms,
        }


def _remove_wall_clock_elapsed(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: _remove_wall_clock_elapsed(item)
            for key, item in value.items()
            if key != "wall_clock_elapsed_ms"
        }
    if isinstance(value, list):
        return [_remove_wall_clock_elapsed(item) for item in value]
    return value


def _teacher_semantic_material_v1(document: Mapping[str, object]) -> dict[str, Any]:
    material = {
        key: _thaw_json_value(value)
        for key, value in document.items()
        if key not in _SEMANTIC_SOURCE_IDENTITY_FIELDS
    }
    return cast(dict[str, Any], _remove_wall_clock_elapsed(material))


def _evidence_identity_material_v1(
    document: Mapping[str, object],
) -> dict[str, object]:
    return {
        "learning_corpus_strategy_teacher_evidence_version": (
            document["learning_corpus_strategy_teacher_evidence_version"]
        ),
        "match_snapshot_id": document["match_snapshot_id"],
        "decision_reference_id": document["decision_reference_id"],
        "source_binding_id": document["source_binding_id"],
        "source_report_fingerprint": document["source_report_fingerprint"],
        "teacher_semantic_fingerprint": document["teacher_semantic_fingerprint"],
    }


def _serialize_evidence_values(values: Mapping[str, object]) -> dict[str, Any]:
    return {
        "learning_corpus_strategy_teacher_evidence_version": (
            LEARNING_CORPUS_STRATEGY_TEACHER_EVIDENCE_VERSION
        ),
        **{key: _json_value(value) for key, value in values.items()},
    }


def _build_strategy_teacher_evidence_v1(
    **values: Any,
) -> LearningCorpusStrategyTeacherEvidenceV1:
    document = _serialize_evidence_values(values)
    teacher_semantic_fingerprint = _build_identifier(
        _SEMANTIC_FINGERPRINT_DOMAIN,
        _teacher_semantic_material_v1(document),
    )
    document["teacher_semantic_fingerprint"] = teacher_semantic_fingerprint
    strategy_teacher_evidence_id = _build_identifier(
        _EVIDENCE_ID_DOMAIN,
        _evidence_identity_material_v1(document),
    )
    return LearningCorpusStrategyTeacherEvidenceV1._from_validated(
        strategy_teacher_evidence_id=strategy_teacher_evidence_id,
        teacher_semantic_fingerprint=teacher_semantic_fingerprint,
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusStrategyTeacherEvidenceCollectionV1:
    """Canonical Strategy Teacher Evidence over explicit Current Match Snapshots."""

    learning_corpus_strategy_teacher_collection_version: int = (
        LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION
    )
    strategy_teacher_collection_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    source_report_count: int
    evidence_count: int
    distinct_decision_count: int
    recommendation_available_count: int
    recommendation_unavailable_count: int
    immediate_requested_count: int
    bounded_search_requested_count: int
    auto_requested_count: int
    information_set_search_requested_count: int
    search_not_attempted_count: int
    search_attempted_count: int
    search_complete_count: int
    search_partial_count: int
    search_timeout_count: int
    search_unavailable_count: int
    fallback_count: int
    profile_presets_enabled_count: int
    profile_application_summary_count: int
    evidences: tuple[LearningCorpusStrategyTeacherEvidenceV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusStrategyTeacherEvidenceCollectionV1 must be "
            "constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusStrategyTeacherEvidenceCollectionV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_strategy_teacher_collection_version",
            LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(
            verify_fingerprint=False,
            verify_evidence_identities=False,
        )
        return value

    def _validate(
        self,
        *,
        verify_fingerprint: bool,
        verify_evidence_identities: bool = True,
    ) -> None:
        _require_version(
            self.learning_corpus_strategy_teacher_collection_version,
            LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION,
            "learning_corpus_strategy_teacher_collection_version",
        )
        _require_hash(
            self.strategy_teacher_collection_fingerprint,
            "strategy_teacher_collection_fingerprint",
        )
        _require_identifier(self.corpus_id, "corpus_id")
        _require_non_negative_integer(
            self.source_catalog_revision,
            "source_catalog_revision",
        )
        _require_hash(self.source_catalog_fingerprint, "source_catalog_fingerprint")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        _require_hash_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
        )
        count_fields = (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "source_report_count",
            "evidence_count",
            "distinct_decision_count",
            "recommendation_available_count",
            "recommendation_unavailable_count",
            "immediate_requested_count",
            "bounded_search_requested_count",
            "auto_requested_count",
            "information_set_search_requested_count",
            "search_not_attempted_count",
            "search_attempted_count",
            "search_complete_count",
            "search_partial_count",
            "search_timeout_count",
            "search_unavailable_count",
            "fallback_count",
            "profile_presets_enabled_count",
            "profile_application_summary_count",
        )
        for field_name in count_fields:
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.retained_match_snapshot_count < self.current_match_count:
            raise ValueError("Retained Snapshot count cannot be below Current count.")
        if type(self.evidences) is not tuple:
            raise ValueError("evidences must be an immutable tuple.")
        for evidence in self.evidences:
            if type(evidence) is not LearningCorpusStrategyTeacherEvidenceV1:
                raise ValueError("evidences must contain exact Strategy Teacher values.")
            evidence._validate(verify_identities=verify_evidence_identities)
        if self.evidences != tuple(
            sorted(self.evidences, key=_strategy_teacher_evidence_sort_key_v1)
        ):
            raise ValueError("Strategy Teacher Evidence must use canonical order.")
        if len({item.strategy_teacher_evidence_id for item in self.evidences}) != len(
            self.evidences
        ):
            raise ValueError("Strategy Teacher Evidence IDs must be unique.")
        if len({item.source_binding_id for item in self.evidences}) != len(self.evidences):
            raise ValueError("Strategy Teacher source bindings must be unique.")
        report_keys = {
            (item.match_snapshot_id, item.source_report_fingerprint) for item in self.evidences
        }
        if len(report_keys) != len(self.evidences):
            raise ValueError("Each exact source Report may occur once per Snapshot.")
        if any(
            item.match_snapshot_id not in self.current_match_snapshot_ids for item in self.evidences
        ):
            raise ValueError("Strategy Teacher Evidence must use Current Snapshots.")

        expected_counts = _strategy_teacher_counts_v1(self.evidences)
        if self.source_report_count != len(self.evidences):
            raise ValueError("source_report_count must reconcile exactly.")
        if self.evidence_count != len(self.evidences):
            raise ValueError("evidence_count must reconcile exactly.")
        for field_name, expected in expected_counts.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"{field_name} must reconcile exactly.")
        if verify_fingerprint:
            expected = _build_identifier(
                _COLLECTION_FINGERPRINT_DOMAIN,
                _collection_fingerprint_material_v1(self),
            )
            if self.strategy_teacher_collection_fingerprint != expected:
                raise ValueError(
                    "strategy_teacher_collection_fingerprint must cover the exact collection."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_strategy_teacher_collection_version": (
                self.learning_corpus_strategy_teacher_collection_version
            ),
            "strategy_teacher_collection_fingerprint": (
                self.strategy_teacher_collection_fingerprint
            ),
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "source_report_count": self.source_report_count,
            "evidence_count": self.evidence_count,
            "distinct_decision_count": self.distinct_decision_count,
            "recommendation_available_count": self.recommendation_available_count,
            "recommendation_unavailable_count": (self.recommendation_unavailable_count),
            "immediate_requested_count": self.immediate_requested_count,
            "bounded_search_requested_count": self.bounded_search_requested_count,
            "auto_requested_count": self.auto_requested_count,
            "information_set_search_requested_count": (self.information_set_search_requested_count),
            "search_not_attempted_count": self.search_not_attempted_count,
            "search_attempted_count": self.search_attempted_count,
            "search_complete_count": self.search_complete_count,
            "search_partial_count": self.search_partial_count,
            "search_timeout_count": self.search_timeout_count,
            "search_unavailable_count": self.search_unavailable_count,
            "fallback_count": self.fallback_count,
            "profile_presets_enabled_count": self.profile_presets_enabled_count,
            "profile_application_summary_count": (self.profile_application_summary_count),
            "evidences": [item.to_dict() for item in self.evidences],
        }


def _strategy_teacher_evidence_sort_key_v1(
    evidence: LearningCorpusStrategyTeacherEvidenceV1,
) -> tuple[object, ...]:
    return (
        evidence.match_id,
        evidence.match_position,
        evidence.decision_index,
        _METHOD_ORDER[evidence.options.recommendation_method],
        evidence.source_report_fingerprint,
        evidence.strategy_teacher_evidence_id,
    )


def _strategy_teacher_counts_v1(
    evidences: tuple[LearningCorpusStrategyTeacherEvidenceV1, ...],
) -> dict[str, int]:
    search_counts = {
        status: sum(item.search_status == status for item in evidences)
        for status in LEARNING_CORPUS_STRATEGY_TEACHER_SEARCH_STATUSES
    }
    return {
        "distinct_decision_count": len({item.decision_reference_id for item in evidences}),
        "recommendation_available_count": sum(
            item.status == "recommendation_available" for item in evidences
        ),
        "recommendation_unavailable_count": sum(
            item.status == "recommendation_unavailable" for item in evidences
        ),
        "immediate_requested_count": sum(
            item.options.recommendation_method == "immediate_expected_value" for item in evidences
        ),
        "bounded_search_requested_count": sum(
            item.options.recommendation_method == "bounded_search" for item in evidences
        ),
        "auto_requested_count": sum(
            item.options.recommendation_method == "auto" for item in evidences
        ),
        "information_set_search_requested_count": sum(
            item.options.recommendation_method == "information_set_search" for item in evidences
        ),
        "search_not_attempted_count": search_counts["not_attempted"],
        "search_attempted_count": len(evidences) - search_counts["not_attempted"],
        "search_complete_count": search_counts["complete"],
        "search_partial_count": search_counts["partial"],
        "search_timeout_count": search_counts["timeout"],
        "search_unavailable_count": search_counts["unavailable"],
        "fallback_count": sum(
            item.recommendation_method_summary.get("fallback_used") is True for item in evidences
        ),
        "profile_presets_enabled_count": sum(
            item.profile_preset_settings.get("use_profile_presets") is True for item in evidences
        ),
        "profile_application_summary_count": sum(
            item.opponent_profile_application_summary is not None for item in evidences
        ),
    }


def _collection_fingerprint_material_v1(
    collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
) -> dict[str, Any]:
    material = collection.to_dict()
    del material["strategy_teacher_collection_fingerprint"]
    return material


def _build_collection_fingerprint_v1(value: object) -> str:
    return _build_identifier(_COLLECTION_FINGERPRINT_DOMAIN, value)


def _validate_learning_corpus_strategy_teacher_collection_v1(
    collection: LearningCorpusStrategyTeacherEvidenceCollectionV1,
) -> None:
    if type(collection) is not LearningCorpusStrategyTeacherEvidenceCollectionV1:
        raise ValueError(
            "collection must be an exact LearningCorpusStrategyTeacherEvidenceCollectionV1."
        )
    collection._validate(verify_fingerprint=True)
