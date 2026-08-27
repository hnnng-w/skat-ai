from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.bounded_search_result import build_serializable_bounded_search_result
from skat_ai.errors import SkatAIInformationPolicyError, SkatAIValidationError
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_json_pointer,
    parse_json_pointer,
    resolve_json_pointer,
)
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
)
from skat_ai.field_provenance_policy import (
    InformationUseContext,
    validate_field_provenance_entry_use,
)
from skat_ai.game_declaration import build_serializable_game_declaration
from skat_ai.hidden_card_inference import build_hidden_card_inference_summary
from skat_ai.information_set_search_comparison import (
    InformationSetSearchComparisonPreActualAnalysisV1,
)
from skat_ai.information_set_search_provenance import (
    build_information_set_search_comparison_provenance_entries,
    build_information_set_search_provenance_entries,
    information_set_settings_reference,
)
from skat_ai.public_hand_constraint import build_serializable_public_hand_constraints
from skat_ai.recommendation_workflow import (
    RecommendationWorkflowResult,
    build_recommendation_method_summary,
)
from skat_ai.result_serialization import build_serializable_game_state
from skat_ai.search_provenance import build_bounded_search_provenance_entries
from skat_ai.v1_information_provenance_sources import exact_v1_json_equal

RETROSPECTIVE_REVIEW_PROVENANCE_VERSION = 1

RETROSPECTIVE_PROVENANCE_STAGES = (
    "decision_input",
    "decision_time_analysis",
    "actual_card_attachment",
    "retrospective_assessment",
    "prioritization",
    "guidance",
    "final_report",
)

_PRIVATE_FIELD_NAMES = {
    "final_hidden_hand",
    "final_hidden_hands",
    "private_remaining_hands",
    "selected_worlds",
    "selected_compatible_worlds",
    "ownership",
    "ownership_assignments",
    "exact_search_state",
    "exact_search_states",
    "derived_child_seed",
    "derived_child_seeds",
    "cache",
    "caches",
    "branches",
    "principal_variation",
    "principal_variations",
    "controlled_policy",
    "information_set",
    "observation",
    "observations",
    "world_states",
    "root_information_set",
    "own_remaining_hand",
    "memoization",
    "bundle_cache",
    "private_profile_record",
    "private_sentinel",
}


def _reference(
    reference_type: str,
    reference_id: str,
    *,
    visibility: str = "public",
    field_path: str | None = None,
) -> FieldProvenanceSourceReference:
    return FieldProvenanceSourceReference(
        reference_type=reference_type,
        reference_id=reference_id,
        field_path=field_path,
        visibility=visibility,
    )


def _entry(
    field_path: str,
    *,
    origin: str,
    visibility: str,
    available_from: str,
    derivation: str,
    decision_index: int | None,
    perspective_player_id: str | None,
    source_references: tuple[FieldProvenanceSourceReference, ...],
    dependency_paths: tuple[str, ...] = (),
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=field_path,
        coverage_kind="field",
        origin=origin,
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=(
            decision_index
            if available_from in {"current_decision", "after_actual_play"}
            else None
        ),
        available_from_event_index=None,
        derivation=derivation,
        source_references=source_references,
        dependency_paths=dependency_paths,
        subject_player_id=None,
        perspective_player_id=perspective_player_id,
    )


def validate_retrospective_provenance_dependency(
    *,
    consumer_stage: str,
    dependency_stage: str,
    path: str = "",
) -> None:
    """Rejects a workflow dependency on information from a later stage."""
    if consumer_stage not in RETROSPECTIVE_PROVENANCE_STAGES:
        raise ValueError(f"Unsupported retrospective consumer stage: {consumer_stage}")
    if dependency_stage not in RETROSPECTIVE_PROVENANCE_STAGES:
        raise ValueError(f"Unsupported retrospective dependency stage: {dependency_stage}")
    if RETROSPECTIVE_PROVENANCE_STAGES.index(dependency_stage) > (
        RETROSPECTIVE_PROVENANCE_STAGES.index(consumer_stage)
    ):
        raise SkatAIInformationPolicyError(
            "Retrospective provenance cannot depend on information from a later stage.",
            path=path,
        )


def validate_provenance_document_redaction(
    value: object,
    *,
    path: str = "",
    allowed_private_field_names: frozenset[str] = frozenset(),
) -> None:
    """Rejects engine-private field names from an attachment document."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            current_path = f"{path}/{key}" if path else f"/{key}"
            if key in _PRIVATE_FIELD_NAMES and key not in allowed_private_field_names:
                raise SkatAIInformationPolicyError(
                    "Engine-private information cannot enter retrospective provenance.",
                    path=current_path,
                )
            validate_provenance_document_redaction(
                item,
                path=current_path,
                allowed_private_field_names=allowed_private_field_names,
            )
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            current_path = f"{path}/{index}" if path else f"/{index}"
            validate_provenance_document_redaction(
                item,
                path=current_path,
                allowed_private_field_names=allowed_private_field_names,
            )


EntryBuilder = Callable[[str, tuple[str, ...]], FieldProvenanceEntry]


def build_complete_provenance_attachment(
    *,
    name: str,
    document_role: str,
    document: Mapping[str, object],
    information_use_context: InformationUseContext,
    entry_builder: EntryBuilder,
    override_entries: tuple[FieldProvenanceEntry, ...] = (),
    validate_entry_use: bool = True,
    allowed_private_field_names: frozenset[str] = frozenset(),
) -> ApplicationProvenanceAttachment:
    """Builds and validates one exact all-leaf non-legacy attachment."""
    validate_provenance_document_redaction(
        document,
        allowed_private_field_names=allowed_private_field_names,
    )
    overrides = {entry.field_path: entry for entry in override_entries}
    if len(overrides) != len(override_entries):
        raise ValueError("Provenance override paths must be unique.")
    leaf_paths = enumerate_json_leaf_paths(document)
    missing = sorted(set(overrides) - set(leaf_paths))
    if missing:
        raise ValueError(f"Provenance override paths are absent: {missing}")
    entries = tuple(
        overrides.get(path, entry_builder(path, parse_json_pointer(path)))
        for path in leaf_paths
    )
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=entries,
        exemptions=(),
        limitations=(),
    )
    coverage = build_field_provenance_coverage_summary(document, ledger)
    if validate_entry_use:
        for provenance_entry in ledger.entries:
            validate_field_provenance_entry_use(
                provenance_entry,
                information_use_context,
            )
    return ApplicationProvenanceAttachment(
        name=name,
        document_role=document_role,
        document=document,
        ledger=ledger,
        coverage_summary=coverage,
        information_use_context=information_use_context,
    )


def _position_context(*, stage: str) -> InformationUseContext:
    return InformationUseContext(
        workflow="position_analysis",
        stage=stage,
        perspective_player_id="me",
        perspective_side=None,
        decision_index=0,
        event_index=None,
    )


def _flat_input_entry(
    path: str,
    tokens: tuple[str, ...],
    *,
    source_document: Mapping[str, object],
    retained_document: Mapping[str, object],
) -> FieldProvenanceEntry:
    local_private = len(tokens) >= 2 and tokens[:2] in {
        ("game_state", "hand"),
        ("game_state", "skat"),
    }
    public_event = len(tokens) >= 2 and tokens[0] == "game_state" and tokens[1] in {
        "current_trick",
        "played_cards",
        "completed_tricks",
        "declarer_points",
        "defender_points",
        "next_player",
        "trick_leader",
    }
    source_declaration = source_document.get("game_declaration")
    source_matadors = (
        source_declaration.get("matadors")
        if isinstance(source_declaration, Mapping)
        else None
    )
    if source_matadors is None:
        source_matadors = source_document.get("matadors")
    if local_private:
        origin = "historical_replay"
        derivation = "reconstruction"
        references = (
            _reference(
                "request",
                "retrospective_position_request",
                field_path=build_json_pointer(tokens[1:]),
            ),
            _reference("algorithm", "retrospective_position_analysis"),
        )
    elif tokens[0] == "selection":
        origin = "rule_derived"
        derivation = "deterministic_rule"
        references = (
            _reference("request", "retrospective_position_request"),
            _reference("request", "position_analysis_options"),
        )
    elif tokens == ("game_declaration", "matadors") and type(source_matadors) is not int:
        origin = "structural_inference"
        derivation = "exact_aggregate"
        references = (_reference("algorithm", "position_matador_inference_v1"),)
    elif public_event or tokens[0] in {
        "opponent_hand_sizes",
        "public_hand_constraints",
    }:
        if tokens[0] == "opponent_hand_sizes":
            source_path = f"/{tokens[1]}_hand_size"
        elif tokens[0] == "game_state":
            source_path = build_json_pointer(tokens[1:])
        else:
            source_path = build_json_pointer(tokens)
        try:
            source_value = resolve_json_pointer(source_document, source_path)
            retained_value = resolve_json_pointer(retained_document, path)
        except SkatAIValidationError:
            exact_public_value = False
        else:
            exact_public_value = exact_v1_json_equal(source_value, retained_value)
        if exact_public_value:
            origin = "public_game_event"
            derivation = "direct"
            references = (
                _reference(
                    "request",
                    "retrospective_position_public_state",
                    field_path=source_path,
                ),
            )
        else:
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (
                _reference("request", "retrospective_position_request"),
                _reference("algorithm", "retrospective_position_analysis"),
            )
    else:
        source_path = None
        retained_value = resolve_json_pointer(retained_document, path)
        for start in range(len(tokens)):
            candidate = build_json_pointer(tokens[start:])
            try:
                source_value = resolve_json_pointer(source_document, candidate)
            except SkatAIValidationError:
                continue
            if exact_v1_json_equal(source_value, retained_value):
                source_path = candidate
                break
        if source_path is not None:
            origin = "validated_copy"
            derivation = "validated"
            references = (
                _reference(
                    "request",
                    "retrospective_position_request",
                    field_path=source_path,
                ),
            )
        else:
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (
                _reference("request", "retrospective_position_request"),
                _reference("algorithm", "retrospective_position_analysis"),
            )
    return _entry(
        path,
        origin=origin,
        visibility="post_game_only" if local_private else "public",
        available_from="game_end" if local_private else "current_decision",
        derivation=derivation,
        decision_index=None if local_private else 0,
        perspective_player_id="me",
        source_references=references,
    )


def build_flat_retrospective_input_attachment(
    *,
    state: object,
    left_hand_size: int,
    right_hand_size: int,
    public_hand_constraints: tuple[object, ...],
    strategic_metadata: object,
    game_declaration: object,
    selection_method: str,
    selection_settings: Mapping[str, object],
    source_document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    """Builds the pre-recommendation flat review input without the actual card."""
    document = {
        "game_state": build_serializable_game_state(state),
        "opponent_hand_sizes": {
            "left": left_hand_size,
            "right": right_hand_size,
        },
        "public_hand_constraints": build_serializable_public_hand_constraints(
            public_hand_constraints
        ),
        "strategic_metadata": {
            "analysis_mode": strategic_metadata.analysis_mode,
            "skat_visibility": strategic_metadata.skat_visibility,
            "game_end_reason": strategic_metadata.game_end_reason,
        },
        "game_declaration": build_serializable_game_declaration(game_declaration),
        "selection": {
            "method": selection_method,
            "settings": dict(selection_settings),
        },
    }
    if strategic_metadata.analysis_mode != "post_game_review":
        raise SkatAIInformationPolicyError(
            "Flat retrospective provenance requires post_game_review mode.",
            path="/strategic_metadata/analysis_mode",
        )
    return build_complete_provenance_attachment(
        name="flat_retrospective/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_position_context(stage="offline_review"),
        entry_builder=lambda path, tokens: _flat_input_entry(
            path,
            tokens,
            source_document=source_document,
            retained_document=document,
        ),
    )


def _decision_analysis_entry(
    path: str,
    _tokens: tuple[str, ...],
) -> FieldProvenanceEntry:
    return _entry(
        path,
        origin="heuristic_analysis",
        visibility="public",
        available_from="current_decision",
        derivation="heuristic",
        decision_index=0,
        perspective_player_id="me",
        source_references=(_reference("algorithm", "retrospective_position_analysis"),),
    )


def _retrospective_assessment_entry(
    path: str,
    tokens: tuple[str, ...],
) -> FieldProvenanceEntry:
    is_actual = tokens[-1] in {"actual_card_played", "actual_card"}
    return _entry(
        path,
        origin="retrospective_attachment" if is_actual else "heuristic_analysis",
        visibility="public",
        available_from="after_actual_play",
        derivation="retrospective" if is_actual else "heuristic",
        decision_index=0,
        perspective_player_id="me",
        source_references=(
            _reference(
                "retrospective_observation" if is_actual else "algorithm",
                "flat_actual_card" if is_actual else "post_game_review",
            ),
        ),
    )


def build_flat_retrospective_result_entries(
    result: Mapping[str, object],
    *,
    actual_card_available: bool,
) -> tuple[FieldProvenanceEntry, ...]:
    """Builds real Result entries for the two flat retrospective branches."""
    entries: list[FieldProvenanceEntry] = []
    for branch in (
        "post_game_review_summary",
        "bounded_search_post_game_review_summary",
    ):
        value = result.get(branch)
        if value is None and branch not in result:
            continue
        for relative_path in enumerate_json_leaf_paths(value):
            full_path = f"/{branch}{relative_path}"
            if actual_card_available:
                entries.append(
                    _retrospective_assessment_entry(
                        full_path,
                        parse_json_pointer(full_path),
                    )
                )
            else:
                entries.append(
                    _decision_analysis_entry(
                        full_path,
                        parse_json_pointer(full_path),
                    )
                )
    return tuple(entries)


class FlatRetrospectiveProvenanceCollector:
    """Retains flat review stages without rerunning recommendation work."""

    def __init__(self, source_document: Mapping[str, object]) -> None:
        if not isinstance(source_document, Mapping):
            raise ValueError("source_document must be an object.")
        self._source_document = source_document
        self._input_attachment: ApplicationProvenanceAttachment | None = None
        self._analysis_document: dict[str, object] | None = None
        self._analysis_results: dict[str, RecommendationWorkflowResult] = {}
        self._assessment_document: dict[str, object] | None = None
        self._actual_card_available = False
        self._information_set_pre_actual: (
            InformationSetSearchComparisonPreActualAnalysisV1 | None
        ) = None

    def capture_flat_decision(self, **kwargs: Any) -> None:
        if self._input_attachment is not None:
            raise ValueError("Flat retrospective input was captured twice.")
        kwargs.pop("decision_index")
        kwargs.pop("simulation_scope", None)
        kwargs["source_document"] = self._source_document
        self._input_attachment = build_flat_retrospective_input_attachment(**kwargs)

    def retain_flat_recommendation_result(
        self,
        result: RecommendationWorkflowResult,
    ) -> None:
        validate_retrospective_provenance_dependency(
            consumer_stage="decision_time_analysis",
            dependency_stage="decision_input",
            path="/flat_retrospective/analysis",
        )
        if self._input_attachment is None:
            raise SkatAIInformationPolicyError(
                "Flat retrospective analysis requires validated decision input.",
                path="/flat_retrospective/analysis",
            )
        self._analysis_document = {
            "primary_analysis": self._serialize_recommendation_result(result),
        }
        self._analysis_results["primary_analysis"] = result

    def retain_flat_immediate_baseline(
        self,
        result: RecommendationWorkflowResult,
    ) -> None:
        if self._analysis_document is None:
            raise SkatAIInformationPolicyError(
                "Immediate baseline provenance requires the primary analysis.",
                path="/flat_retrospective/analysis/immediate_baseline",
            )
        self._analysis_document["immediate_baseline"] = (
            self._serialize_recommendation_result(result)
        )
        self._analysis_results["immediate_baseline"] = result

    def retain_flat_information_set_search_pre_actual_analysis(
        self,
        analysis: InformationSetSearchComparisonPreActualAnalysisV1,
    ) -> None:
        if not isinstance(
            analysis,
            InformationSetSearchComparisonPreActualAnalysisV1,
        ):
            raise ValueError("Information-set comparison analysis has the wrong type.")
        if self._analysis_document is None:
            raise SkatAIInformationPolicyError(
                "Information-set baseline provenance requires the primary analysis.",
                path="/flat_retrospective/analysis/same_selection_pimc_result",
            )
        self._information_set_pre_actual = analysis
        self._analysis_document["same_selection_pimc_result"] = (
            build_serializable_bounded_search_result(analysis.pimc_result)
            if analysis.pimc_result is not None
            else None
        )

    def retain_flat_retrospective_assessment(
        self,
        *,
        actual_card_played: str | None,
        post_game_review_summary: Mapping[str, object],
        bounded_search_post_game_review_summary: Mapping[str, object] | None,
        information_set_search_comparison: Mapping[str, object] | None = None,
    ) -> None:
        if actual_card_played is None:
            return
        validate_retrospective_provenance_dependency(
            consumer_stage="retrospective_assessment",
            dependency_stage="actual_card_attachment",
            path="/flat_retrospective/assessment",
        )
        if self._analysis_document is None:
            raise SkatAIInformationPolicyError(
                "Flat retrospective assessment requires decision-time analysis.",
                path="/flat_retrospective/assessment",
            )
        self._actual_card_available = True
        document: dict[str, object] = {
            "actual_card_played": actual_card_played,
            "post_game_review_summary": dict(post_game_review_summary),
        }
        if bounded_search_post_game_review_summary is not None:
            document["bounded_search_post_game_review_summary"] = dict(
                bounded_search_post_game_review_summary
            )
        if information_set_search_comparison is not None:
            document["information_set_search_comparison"] = dict(
                information_set_search_comparison
            )
        self._assessment_document = document

    @staticmethod
    def _serialize_recommendation_result(
        result: RecommendationWorkflowResult,
    ) -> dict[str, object]:
        inference = build_hidden_card_inference_summary(
            result.hidden_card_inference_model
        )
        document: dict[str, object] = {
            "legal_cards": list(result.legal_cards),
            "recommendation": {
                "card": result.recommendation_card,
                "reason": result.recommendation_reason,
            },
            "analysis_report": [dict(row) for row in result.analysis_report],
            "strategic_summary": result.strategic_summary,
            "recommendation_method_summary": build_recommendation_method_summary(
                result
            ),
            "bounded_search_result": (
                build_serializable_bounded_search_result(result.bounded_search_result)
                if result.bounded_search_result is not None
                else None
            ),
            "information_set_search_result": (
                dict(result.information_set_search_public_result)
                if result.information_set_search_public_result is not None
                else None
            ),
            "hidden_card_inference_summary": inference,
        }
        return document

    def _build_analysis_attachment(self) -> ApplicationProvenanceAttachment:
        if self._analysis_document is None:
            raise SkatAIInformationPolicyError(
                "Flat retrospective analysis was not retained.",
                path="/flat_retrospective/analysis",
            )
        overrides: list[FieldProvenanceEntry] = []
        for section_name, retained in self._analysis_results.items():
            if retained.bounded_search_result is not None:
                overrides.extend(
                    search_entries_for_nested_result(
                        retained.bounded_search_result,
                        field_path=f"/{section_name}/bounded_search_result",
                        decision_index=0,
                        perspective_player_id="me",
                    )
                )
            if retained.information_set_search_public_result is not None:
                overrides.extend(
                    build_information_set_search_provenance_entries(
                        retained.information_set_search_public_result,
                        retained_result=retained.information_set_search_result,
                        field_path=(
                            f"/{section_name}/information_set_search_result"
                        ),
                        decision_index=0,
                        perspective_player_id="me",
                        settings_reference=information_set_settings_reference(
                            "request",
                            "position_analysis_request",
                            field_path="/information_set_search_settings",
                        ),
                        fixed_policy_reference=information_set_settings_reference(
                            "algorithm",
                            "effective_opponent_policy",
                        ),
                    )
                )
        if (
            self._information_set_pre_actual is not None
            and self._information_set_pre_actual.pimc_result is not None
        ):
            overrides.extend(
                search_entries_for_nested_result(
                    self._information_set_pre_actual.pimc_result,
                    field_path="/same_selection_pimc_result",
                    decision_index=0,
                    perspective_player_id="me",
                )
            )
        return build_complete_provenance_attachment(
            name="flat_retrospective/analysis",
            document_role="result",
            document=self._analysis_document,
            information_use_context=_position_context(stage="decision_time"),
            entry_builder=_decision_analysis_entry,
            override_entries=tuple(overrides),
        )

    def _build_assessment_attachment(self) -> ApplicationProvenanceAttachment | None:
        if self._assessment_document is None:
            return None
        overrides: tuple[FieldProvenanceEntry, ...] = ()
        comparison = self._assessment_document.get(
            "information_set_search_comparison"
        )
        if isinstance(comparison, Mapping):
            overrides = build_information_set_search_comparison_provenance_entries(
                comparison,
                field_path="/information_set_search_comparison",
                decision_index=0,
                perspective_player_id="me",
                actual_reference_id="flat_actual_card",
            )
        return build_complete_provenance_attachment(
            name="flat_retrospective/assessment",
            document_role="result",
            document=self._assessment_document,
            information_use_context=_position_context(stage="after_actual_play"),
            entry_builder=_retrospective_assessment_entry,
            override_entries=overrides,
        )

    def build_bundle(
        self,
        result: Mapping[str, object],
        *,
        external_reference: str | None,
        source_document: Mapping[str, object] | None = None,
    ) -> ApplicationProvenanceBundle:
        if self._input_attachment is None:
            raise SkatAIInformationPolicyError(
                "Flat retrospective input was not captured.",
                path="/flat_retrospective/input",
            )
        from skat_ai.live_analysis_provenance import (
            build_live_position_result_provenance_attachment,
        )

        retrospective_entries = build_flat_retrospective_result_entries(
            result,
            actual_card_available=self._actual_card_available,
        )
        search_entries: tuple[FieldProvenanceEntry, ...] = ()
        primary = self._analysis_results.get("primary_analysis")
        if primary is not None and primary.bounded_search_result is not None:
            search_entries = search_entries_for_nested_result(
                primary.bounded_search_result,
                field_path="/bounded_search_result",
                decision_index=0,
                perspective_player_id="me",
            )
        if (
            primary is not None
            and primary.information_set_search_public_result is not None
        ):
            search_entries = (
                *search_entries,
                *build_information_set_search_provenance_entries(
                    primary.information_set_search_public_result,
                    retained_result=primary.information_set_search_result,
                    field_path="/information_set_search_result",
                    decision_index=0,
                    perspective_player_id="me",
                    settings_reference=information_set_settings_reference(
                        "request",
                        "position_analysis_request",
                        field_path="/information_set_search_settings",
                    ),
                    fixed_policy_reference=information_set_settings_reference(
                        "algorithm",
                        "effective_opponent_policy",
                    ),
                ),
            )
        comparison_entries: tuple[FieldProvenanceEntry, ...] = ()
        comparison = result.get("information_set_search_comparison")
        if isinstance(comparison, Mapping):
            comparison_entries = (
                build_information_set_search_comparison_provenance_entries(
                    comparison,
                    field_path="/information_set_search_comparison",
                    decision_index=0,
                    perspective_player_id="me",
                    actual_reference_id="flat_actual_card",
                )
            )
        result_attachment = build_live_position_result_provenance_attachment(
            result,
            search_entries_by_path={
                entry.field_path: entry for entry in search_entries
            },
            external_reference=external_reference,
            source_document=source_document,
            additional_entries_by_path={
                entry.field_path: entry
                for entry in (*retrospective_entries, *comparison_entries)
            },
        )
        assessment = self._build_assessment_attachment()
        attachments = [
            self._input_attachment,
            self._build_analysis_attachment(),
        ]
        if assessment is not None:
            attachments.append(assessment)
        attachments.append(result_attachment)
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            attachments=tuple(attachments),
        )


def search_entries_for_nested_result(
    result: object,
    *,
    field_path: str,
    decision_index: int,
    perspective_player_id: str,
) -> tuple[FieldProvenanceEntry, ...]:
    """Reuses the aggregate Search mapping with the historical local identity."""
    return tuple(
        replace(entry, perspective_player_id=perspective_player_id)
        for entry in build_bounded_search_provenance_entries(
            result,
            field_path=field_path,
            decision_index=decision_index,
        )
    )
