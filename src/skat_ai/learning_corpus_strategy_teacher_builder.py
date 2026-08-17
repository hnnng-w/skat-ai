from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, cast

from skat_ai.api.v1.contracts import (
    RequestDocumentV1,
    ResultDocumentV1,
    WorkflowV1,
)
from skat_ai.api.v1.schema_validation import validate_output_document
from skat_ai.errors import SkatAIInvariantError
from skat_ai.learning_corpus_current_snapshots import (
    resolve_learning_corpus_current_match_snapshots_v1,
)
from skat_ai.learning_corpus_match_snapshot import LearningCorpusMatchSnapshotV1
from skat_ai.learning_corpus_persistence_contracts import (
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION,
    LearningCorpusStrategyTeacherEvidenceCollectionV1,
    LearningCorpusStrategyTeacherEvidenceV1,
    LearningCorpusStrategyTeacherReportSourceV1,
    _build_collection_fingerprint_v1,
    _build_strategy_teacher_evidence_v1,
    _strategy_teacher_counts_v1,
    _strategy_teacher_evidence_sort_key_v1,
)
from skat_ai.match_analysis_contracts import MatchDecisionAnalysisResultV1
from skat_ai.match_decision_analysis import (
    _reconcile_profile_summary,
    build_match_decision_position_request_v1,
)

_SETTINGS_FIELDS = {
    "left_hand_size",
    "right_hand_size",
    "sample_count",
    "random_seed",
    "use_basic_opponent_strategy",
    "recommendation_method",
    "bounded_search_settings",
}
_ANALYSIS_METADATA_FIELDS = {
    "strategic_metadata",
    "left_player_profile",
    "right_player_profile",
    "recommended_opponent_policy_presets",
}
_STRATEGIC_METADATA_FIELDS = {
    "analysis_mode",
    "skat_visibility",
    "game_end_reason",
}
_PLAYER_PROFILE_FIELDS = {
    "games_played",
    "solo_games_played",
    "defender_games_played",
    "solo_rate",
    "defender_rate",
    "solo_win_rate",
    "hand_game_rate",
    "suit_game_rate",
    "grand_rate",
    "null_game_rate",
    "defender_win_rate",
}
_RECOMMENDED_POLICY_PRESET_FIELDS = {
    "left_player_recommended_preset",
    "right_player_recommended_preset",
}
_OPPONENT_POLICY_FIELDS = {
    "opponent_lead_policy",
    "opponent_response_policy",
}
_RECOMMENDATION_FIELDS = {"card", "reason"}
_IMMEDIATE_CANDIDATE_FIELDS = {
    "card",
    "win_rate",
    "average_trick_points",
    "average_points_won",
    "average_points_lost",
    "expected_point_swing",
    "is_recommended",
}
_PLAYER_PROFILE_COUNT_FIELDS = {
    "games_played",
    "solo_games_played",
    "defender_games_played",
}
_PROFILE_POLICY_PRESETS = {
    "simple_lowest",
    "aggressive_points",
    "cautious_defender",
}


def _require_mapping(
    document: Mapping[str, object],
    field_name: str,
    *,
    allow_absent: bool = False,
) -> Mapping[str, object] | None:
    value = document.get(field_name)
    if value is None and allow_absent:
        return None
    if not isinstance(value, Mapping):
        raise SkatAIInvariantError(
            f"Strategy Teacher source Result requires {field_name}."
        )
    return value


def _require_sequence(
    document: Mapping[str, object],
    field_name: str,
) -> Sequence[object]:
    value = document.get(field_name)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SkatAIInvariantError(
            f"Strategy Teacher source Result requires {field_name}."
        )
    return value


def _require_exact_fields(
    value: Mapping[str, object],
    expected_fields: set[str],
    field_name: str,
) -> None:
    if set(value) != expected_fields:
        raise SkatAIInvariantError(
            f"Strategy Teacher source {field_name} fields must be exact."
        )


def _validate_minimized_open_schema_fields(
    *,
    settings: Mapping[str, object],
    analysis_metadata: Mapping[str, object],
    opponent_policy_settings: Mapping[str, object],
    left_opponent_policy_settings: Mapping[str, object],
    right_opponent_policy_settings: Mapping[str, object],
    recommendation: Mapping[str, object],
    immediate_candidates: Sequence[object],
    expected_strategic_metadata: Mapping[str, object],
) -> None:
    _require_exact_fields(settings, _SETTINGS_FIELDS, "settings")
    _require_exact_fields(
        analysis_metadata,
        _ANALYSIS_METADATA_FIELDS,
        "analysis_metadata",
    )
    nested_metadata = (
        (
            "strategic_metadata",
            _STRATEGIC_METADATA_FIELDS,
        ),
        (
            "left_player_profile",
            _PLAYER_PROFILE_FIELDS,
        ),
        (
            "right_player_profile",
            _PLAYER_PROFILE_FIELDS,
        ),
        (
            "recommended_opponent_policy_presets",
            _RECOMMENDED_POLICY_PRESET_FIELDS,
        ),
    )
    for field_name, expected_fields in nested_metadata:
        nested = analysis_metadata.get(field_name)
        if not isinstance(nested, Mapping):
            raise SkatAIInvariantError(
                f"Strategy Teacher source analysis_metadata.{field_name} is invalid."
            )
        _require_exact_fields(
            nested,
            expected_fields,
            f"analysis_metadata.{field_name}",
        )
    strategic_metadata = cast(
        Mapping[str, object],
        analysis_metadata["strategic_metadata"],
    )
    if strategic_metadata != expected_strategic_metadata:
        raise SkatAIInvariantError(
            "Strategy Teacher analysis metadata changed source strategy fields."
        )
    for side in ("left", "right"):
        profile = cast(
            Mapping[str, object],
            analysis_metadata[f"{side}_player_profile"],
        )
        for field_name, field_value in profile.items():
            if field_name in _PLAYER_PROFILE_COUNT_FIELDS:
                valid = field_value is None or (
                    type(field_value) is int and field_value >= 0
                )
            else:
                valid = field_value is None or (
                    type(field_value) in {int, float}
                    and math.isfinite(field_value)
                    and 0.0 <= field_value <= 1.0
                )
            if not valid:
                raise SkatAIInvariantError(
                    "Strategy Teacher analysis metadata contains an invalid "
                    f"{side} Profile value."
                )
    recommended_presets = cast(
        Mapping[str, object],
        analysis_metadata["recommended_opponent_policy_presets"],
    )
    if any(
        value not in _PROFILE_POLICY_PRESETS
        for value in recommended_presets.values()
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher analysis metadata contains an invalid policy preset."
        )
    for field_name, policy in (
        ("opponent_policy_settings", opponent_policy_settings),
        ("left_opponent_policy_settings", left_opponent_policy_settings),
        ("right_opponent_policy_settings", right_opponent_policy_settings),
    ):
        _require_exact_fields(policy, _OPPONENT_POLICY_FIELDS, field_name)
    _require_exact_fields(recommendation, _RECOMMENDATION_FIELDS, "recommendation")
    for index, candidate in enumerate(immediate_candidates):
        if not isinstance(candidate, Mapping):
            raise SkatAIInvariantError(
                "Strategy Teacher Immediate Candidates must be JSON objects."
            )
        _require_exact_fields(
            candidate,
            _IMMEDIATE_CANDIDATE_FIELDS,
            f"analysis_report[{index}]",
        )


def _reconcile_snapshot_source(
    source: LearningCorpusStrategyTeacherReportSourceV1,
    snapshot: LearningCorpusMatchSnapshotV1,
) -> tuple[object, object, str, str]:
    report = source.report
    value = cast(MatchDecisionAnalysisResultV1, report.value)
    workspace = snapshot.workspace
    if (
        source.match_snapshot_id != snapshot.match_snapshot_id
        or report.match_id != snapshot.match_id
        or value.match_id != snapshot.match_id
        or workspace.match_definition.match_id != snapshot.match_id
        or report.workspace_revision != snapshot.workspace_revision
        or value.workspace_revision != snapshot.workspace_revision
        or workspace.revision != snapshot.workspace_revision
    ):
        raise ValueError(
            "Strategy Teacher source must match its explicit Current Snapshot."
        )
    match_position = cast(int, report.match_position)
    decision_index = cast(int, report.decision_index)
    slot = workspace.slots[match_position - 1]
    game = slot.observed_game
    if (
        slot.match_position != match_position
        or game is None
        or game.match_position != match_position
        or value.game_id != game.game_id
    ):
        raise ValueError(
            "Strategy Teacher source must resolve to its exact observed Game."
        )
    game_references = tuple(
        reference
        for reference in snapshot.game_references
        if reference.match_position == match_position
    )
    if len(game_references) != 1:
        raise ValueError(
            "Strategy Teacher source must resolve to one exact Game Reference."
        )
    game_reference = game_references[0]
    if (
        game_reference.match_snapshot_id != snapshot.match_snapshot_id
        or game_reference.match_id != snapshot.match_id
        or game_reference.game_id != game.game_id
    ):
        raise ValueError(
            "Strategy Teacher Game Reference must close to the Current Snapshot."
        )
    decision_references = tuple(
        reference
        for reference in snapshot.decision_references
        if reference.game_reference_id == game_reference.game_reference_id
        and reference.decision_index == decision_index
    )
    plays = tuple(
        play for play in game.plays if play.decision_index == decision_index
    )
    if len(decision_references) != 1 or len(plays) != 1:
        raise ValueError(
            "Strategy Teacher source must resolve to one exact Decision Reference."
        )
    decision_reference = decision_references[0]
    play = plays[0]
    if (
        decision_reference.decision_reference_id
        not in game_reference.decision_reference_ids
        or decision_reference.match_snapshot_id != snapshot.match_snapshot_id
        or decision_reference.match_id != snapshot.match_id
        or decision_reference.game_id != game.game_id
        or decision_reference.match_position != match_position
        or decision_reference.acting_player_id != play.player_id
    ):
        raise ValueError(
            "Strategy Teacher Decision Reference must close to the observed Play."
        )
    return game_reference, decision_reference, play.player_id, play.card


def _rebuild_and_validate_source(
    source: LearningCorpusStrategyTeacherReportSourceV1,
    snapshot: LearningCorpusMatchSnapshotV1,
    *,
    actual_card_played: str,
) -> tuple[MatchDecisionAnalysisResultV1, dict[str, Any]]:
    value = cast(MatchDecisionAnalysisResultV1, source.report.value)
    request = cast(RequestDocumentV1, value.request)
    result = cast(ResultDocumentV1, value.result)
    try:
        prepared = build_match_decision_position_request_v1(
            snapshot.workspace,
            match_position=value.match_position,
            decision_index=value.decision_index,
            options=value.options,
        )
    except Exception as error:
        if isinstance(error, SkatAIInvariantError):
            raise
        raise SkatAIInvariantError(
            "Strategy Teacher could not rebuild the source Position Request."
        ) from error
    if prepared.request != request:
        raise SkatAIInvariantError(
            "Strategy Teacher rebuilt Request differs from the source Request."
        )
    if prepared.profile_binding != value.profile_binding:
        raise SkatAIInvariantError(
            "Strategy Teacher rebuilt Profile binding differs from the source."
        )
    if (
        request.workflow is not WorkflowV1.POSITION_ANALYSIS
        or result.workflow is not WorkflowV1.POSITION_ANALYSIS
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher source must retain Position workflow identity."
        )
    request_document = request.to_dict()["document"]
    result_document = result.to_dict()["document"]
    validate_output_document(result_document)
    if result_document.get("input_file") != prepared.input_reference:
        raise SkatAIInvariantError(
            "Strategy Teacher source Result changed the input reference."
        )
    result_settings = result_document.get("settings")
    expected_settings = {
        field_name: (
            request_document.get(field_name)
            if field_name == "bounded_search_settings"
            else request_document[field_name]
        )
        for field_name in _SETTINGS_FIELDS
    }
    if (
        not isinstance(result_settings, Mapping)
        or result_settings != expected_settings
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher Result changed rebuilt Request settings."
        )
    _reconcile_profile_summary(result_document, prepared)
    review = _require_mapping(result_document, "post_game_review_summary")
    if (
        request_document.get("actual_card_played") != actual_card_played
        or review is None
        or review.get("actual_card_played") != actual_card_played
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher source changed the observed actual Card."
        )
    return value, result_document


def _extract_evidence(
    source: LearningCorpusStrategyTeacherReportSourceV1,
    snapshot: LearningCorpusMatchSnapshotV1,
) -> LearningCorpusStrategyTeacherEvidenceV1:
    (
        game_reference,
        decision_reference,
        acting_player_id,
        actual_card_played,
    ) = _reconcile_snapshot_source(source, snapshot)
    value, result = _rebuild_and_validate_source(
        source,
        snapshot,
        actual_card_played=actual_card_played,
    )
    settings = cast(Mapping[str, object], _require_mapping(result, "settings"))
    analysis_metadata = cast(
        Mapping[str, object],
        _require_mapping(result, "analysis_metadata"),
    )
    information_policy_summary = cast(
        Mapping[str, object],
        _require_mapping(result, "information_policy_summary"),
    )
    opponent_policy_settings = cast(
        Mapping[str, object],
        _require_mapping(result, "opponent_policy_settings"),
    )
    left_opponent_policy_settings = cast(
        Mapping[str, object],
        _require_mapping(result, "left_opponent_policy_settings"),
    )
    right_opponent_policy_settings = cast(
        Mapping[str, object],
        _require_mapping(result, "right_opponent_policy_settings"),
    )
    profile_preset_settings = cast(
        Mapping[str, object],
        _require_mapping(result, "profile_preset_settings"),
    )
    recommendation_method_summary = cast(
        Mapping[str, object],
        _require_mapping(result, "recommendation_method_summary"),
    )
    recommendation = cast(
        Mapping[str, object],
        _require_mapping(result, "recommendation"),
    )
    review = cast(
        Mapping[str, object],
        _require_mapping(result, "post_game_review_summary"),
    )
    immediate_candidates = _require_sequence(result, "analysis_report")
    _validate_minimized_open_schema_fields(
        settings=settings,
        analysis_metadata=analysis_metadata,
        opponent_policy_settings=opponent_policy_settings,
        left_opponent_policy_settings=left_opponent_policy_settings,
        right_opponent_policy_settings=right_opponent_policy_settings,
        recommendation=recommendation,
        immediate_candidates=immediate_candidates,
        expected_strategic_metadata={
            "analysis_mode": "post_game_review",
            "skat_visibility": cast(RequestDocumentV1, value.request).document[
                "skat_visibility"
            ],
            "game_end_reason": "not_ended",
        },
    )
    profile_summary = _require_mapping(
        result,
        "opponent_profile_application_summary",
        allow_absent=True,
    )
    search = _require_mapping(
        result,
        "bounded_search_result",
        allow_absent=True,
    )
    search_review = _require_mapping(
        result,
        "bounded_search_post_game_review_summary",
        allow_absent=True,
    )
    requested_method = recommendation_method_summary.get("requested_method")
    if (
        requested_method != value.options.recommendation_method
        or settings.get("recommendation_method") != requested_method
        or profile_preset_settings.get("use_profile_presets")
        != value.options.use_profile_presets
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher Result settings differ from source options."
        )
    if (
        settings.get("sample_count") != value.options.immediate_sample_count
        or settings.get("random_seed") != value.options.immediate_random_seed
    ):
        raise SkatAIInvariantError(
            "Strategy Teacher Result changed Immediate analysis options."
        )
    search_attempted = recommendation_method_summary.get("search_attempted")
    if search_attempted is True:
        if search is None or search_review is None:
            raise SkatAIInvariantError(
                "Strategy Teacher attempted Search requires Search evidence."
            )
        actual_comparison = search_review.get("search_actual_card_comparison")
        if (
            not isinstance(actual_comparison, Mapping)
            or actual_comparison.get("actual_card") != actual_card_played
        ):
            raise SkatAIInvariantError(
                "Strategy Teacher Search review changed the observed actual Card."
            )
        search_status = cast(str, search.get("status"))
        search_stop_reason = cast(str, search.get("stop_reason"))
        world_coverage = cast(str, search.get("world_coverage"))
        solution_claim = cast(str, search.get("solution_claim"))
        requested_budget = cast(Mapping[str, object], search.get("requested_budget"))
        consumed_budget = cast(Mapping[str, object], search.get("consumed_budget"))
        search_candidate_results = cast(
            Sequence[object], search.get("candidate_results")
        )
        if (
            not isinstance(requested_budget, Mapping)
            or not isinstance(consumed_budget, Mapping)
            or isinstance(search_candidate_results, (str, bytes))
            or not isinstance(search_candidate_results, Sequence)
        ):
            raise SkatAIInvariantError(
                "Strategy Teacher Search evidence is structurally incomplete."
            )
        wall_clock_elapsed_ms = consumed_budget.get("wall_clock_elapsed_ms")
    elif search_attempted is False:
        search_status = "not_attempted"
        search_stop_reason = None
        world_coverage = None
        solution_claim = None
        requested_budget = None
        consumed_budget = None
        search_candidate_results = ()
        wall_clock_elapsed_ms = None
    else:
        raise SkatAIInvariantError(
            "Strategy Teacher source Result has invalid Search-attempt state."
        )
    strategic_summary = result.get("strategic_summary")
    if not isinstance(strategic_summary, str):
        raise SkatAIInvariantError(
            "Strategy Teacher source Result requires strategic_summary."
        )
    effective_method = recommendation_method_summary.get("effective_method")
    status = (
        "recommendation_available"
        if recommendation.get("card") is not None and effective_method != "none"
        else "recommendation_unavailable"
    )
    profile_binding = value.profile_binding
    if profile_binding is None:
        raise SkatAIInvariantError(
            "Strategy Teacher source omitted the executed Profile binding."
        )
    return _build_strategy_teacher_evidence_v1(
        source_binding_id=source.source_binding_id,
        source_report_id=source.source_report_id,
        source_report_fingerprint=source.source_report_fingerprint,
        source_request_fingerprint=source.source_request_fingerprint,
        source_result_fingerprint=source.source_result_fingerprint,
        match_snapshot_id=snapshot.match_snapshot_id,
        game_reference_id=game_reference.game_reference_id,
        decision_reference_id=decision_reference.decision_reference_id,
        match_id=snapshot.match_id,
        workspace_revision=snapshot.workspace_revision,
        match_position=value.match_position,
        game_id=cast(str, value.game_id),
        decision_index=value.decision_index,
        acting_player_id=acting_player_id,
        actual_card_played=actual_card_played,
        status=status,
        options=value.options,
        profile_binding=profile_binding,
        settings=settings,
        analysis_metadata=analysis_metadata,
        information_policy_summary=information_policy_summary,
        legal_cards=_require_sequence(result, "legal_cards"),
        opponent_policy_settings=opponent_policy_settings,
        left_opponent_policy_settings=left_opponent_policy_settings,
        right_opponent_policy_settings=right_opponent_policy_settings,
        profile_preset_settings=profile_preset_settings,
        opponent_profile_application_summary=profile_summary,
        recommendation_method_summary=recommendation_method_summary,
        recommendation=recommendation,
        strategic_summary=strategic_summary,
        immediate_candidate_results=immediate_candidates,
        bounded_search_result=search,
        post_game_review_summary=review,
        bounded_search_post_game_review_summary=search_review,
        search_status=search_status,
        search_stop_reason=search_stop_reason,
        world_coverage=world_coverage,
        solution_claim=solution_claim,
        requested_budget=requested_budget,
        consumed_budget=consumed_budget,
        search_candidate_results=search_candidate_results,
        wall_clock_elapsed_ms=wall_clock_elapsed_ms,
    )


def _collection_material(values: Mapping[str, object]) -> dict[str, Any]:
    return {
        "learning_corpus_strategy_teacher_collection_version": (
            LEARNING_CORPUS_STRATEGY_TEACHER_COLLECTION_VERSION
        ),
        **{
            key: (
                [item.to_dict() for item in value]
                if key == "evidences"
                else list(value)
                if key == "current_match_snapshot_ids"
                else value
            )
            for key, value in values.items()
        },
    }


def build_learning_corpus_strategy_teacher_evidence_collection_v1(
    store: LearningCorpusStoreResumeResultV1,
    sources: tuple[LearningCorpusStrategyTeacherReportSourceV1, ...],
) -> LearningCorpusStrategyTeacherEvidenceCollectionV1:
    """Builds method-bound evidence from exact Current-Snapshot Reports."""
    if type(store) is not LearningCorpusStoreResumeResultV1:
        raise ValueError("store must be an exact LearningCorpusStoreResumeResultV1.")
    if type(sources) is not tuple:
        raise ValueError("sources must be an immutable tuple.")
    for source in sources:
        if type(source) is not LearningCorpusStrategyTeacherReportSourceV1:
            raise ValueError(
                "sources must contain exact Strategy Teacher Report Sources."
            )
        source._validate(verify_identities=True, validate_report=True)
    source_binding_ids = tuple(source.source_binding_id for source in sources)
    if len(source_binding_ids) != len(set(source_binding_ids)):
        raise ValueError("Strategy Teacher source-binding IDs must be unique.")
    report_keys = tuple(
        (source.match_snapshot_id, source.source_report_fingerprint)
        for source in sources
    )
    if len(report_keys) != len(set(report_keys)):
        raise ValueError(
            "Each exact source Report may occur once per Match Snapshot."
        )

    current_snapshots = resolve_learning_corpus_current_match_snapshots_v1(store)
    current_by_match_id = {snapshot.match_id: snapshot for snapshot in current_snapshots}
    evidences: list[LearningCorpusStrategyTeacherEvidenceV1] = []
    for source in sources:
        snapshot = current_by_match_id.get(source.report.match_id)
        if snapshot is None or source.match_snapshot_id != snapshot.match_snapshot_id:
            raise ValueError(
                "Strategy Teacher sources must bind the explicit Current Match Snapshot."
            )
        evidences.append(_extract_evidence(source, snapshot))
    ordered_evidences = tuple(
        sorted(evidences, key=_strategy_teacher_evidence_sort_key_v1)
    )
    source_catalog = store.document.catalog
    current_snapshot_ids = tuple(
        selection.match_snapshot_id for selection in source_catalog.current_matches
    )
    collection_values: dict[str, object] = {
        "corpus_id": source_catalog.corpus_id,
        "source_catalog_revision": source_catalog.revision,
        "source_catalog_fingerprint": store.document.catalog_fingerprint,
        "source_catalog_content_fingerprint": store.document.content_fingerprint,
        "current_match_snapshot_ids": current_snapshot_ids,
        "retained_match_snapshot_count": len(store.match_snapshots),
        "current_match_count": len(current_snapshots),
        "orphan_match_snapshot_count": len(store.orphan_match_snapshot_ids),
        "source_report_count": len(sources),
        "evidence_count": len(ordered_evidences),
        **_strategy_teacher_counts_v1(ordered_evidences),
        "evidences": ordered_evidences,
    }
    return LearningCorpusStrategyTeacherEvidenceCollectionV1._from_validated(
        strategy_teacher_collection_fingerprint=_build_collection_fingerprint_v1(
            _collection_material(collection_values)
        ),
        **collection_values,
    )
