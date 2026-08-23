from __future__ import annotations

from collections.abc import Mapping

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
)
from skat_ai.field_provenance_coverage import enumerate_json_leaf_paths
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalDecisionSnapshotSummary,
)
from skat_ai.historical_result_provenance import (
    build_historical_game_result_attachment as _build_complete_historical_game_result_attachment,
)
from skat_ai.historical_search_review import (
    HistoricalSearchDecisionPreActualAnalysis,
    HistoricalSearchDecisionRetrospectiveAttachment,
)
from skat_ai.information_set_search_provenance import (
    build_information_set_search_comparison_provenance_entries,
    build_information_set_search_provenance_entries,
    build_serialized_pimc_provenance_entries,
    information_set_settings_reference,
)
from skat_ai.public_hand_constraint import build_serializable_public_hand_constraints
from skat_ai.replay_coaching_assessment import (
    build_serializable_replay_coaching_decision_assessment,
)
from skat_ai.replay_coaching_evidence import (
    DecisionTimeReplayCoachingEvidence,
    build_serializable_decision_time_replay_coaching_evidence,
)
from skat_ai.replay_coaching_guidance import ReplayCoachingGuidanceResult
from skat_ai.replay_coaching_prioritization import ReplayCoachingPrioritizationResult
from skat_ai.replay_coaching_provenance import (
    build_replay_coaching_guidance_attachment,
    build_replay_coaching_prioritization_attachment,
    build_replay_coaching_report_attachment,
)
from skat_ai.replay_coaching_report import ReplayCoachingReport
from skat_ai.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
    search_entries_for_nested_result,
    validate_retrospective_provenance_dependency,
)
from skat_ai.retrospective_search_comparison import (
    build_serializable_search_actual_card_comparison,
)


def _serialize_play(play: object) -> dict[str, object]:
    return {"player_id": play.player_id, "card": play.card}


def _serialize_visible_state(snapshot: HistoricalDecisionSnapshot) -> dict[str, object]:
    state = snapshot.visible_state
    declaration = state.declaration
    return {
        "game_type": state.game_type,
        "declaration": {
            "hand_game": declaration.hand_game,
            "ouvert": declaration.ouvert,
            "schneider_announced": declaration.schneider_announced,
            "schwarz_announced": declaration.schwarz_announced,
            "matadors": declaration.matadors,
            "bid_value": declaration.bid_value,
        },
        "own_hand": list(state.own_hand),
        "legal_cards": list(state.legal_cards),
        "skat_visibility": state.skat_visibility,
        "known_skat_cards": list(state.known_skat_cards),
        "public_exposed_cards": [
            {
                "player_id": exposure.player_id,
                "cards": list(exposure.cards),
            }
            for exposure in state.public_exposed_cards
        ],
        "completed_tricks": [
            {
                "trick_number": trick.trick_number,
                "plays": [_serialize_play(play) for play in trick.plays],
                "winner_player_id": trick.winner_player_id,
                "winner_side": trick.winner_side,
                "trick_points": trick.trick_points,
            }
            for trick in state.completed_tricks
        ],
        "current_trick": [_serialize_play(play) for play in state.current_trick],
        "declarer_trick_points": state.declarer_trick_points,
        "defender_trick_points": state.defender_trick_points,
        "opponent_hand_sizes": [
            {
                "relative_player": opponent.relative_player,
                "player_id": opponent.player_id,
                "remaining_card_count": opponent.remaining_card_count,
            }
            for opponent in state.opponent_hand_sizes
        ],
    }


def build_historical_decision_input_document(
    snapshot: HistoricalDecisionSnapshot,
    *,
    effective_review_settings: Mapping[str, object],
    external_profile_application: Mapping[str, object] | None = None,
    effective_opponent_policies: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Builds one allowlisted pre-actual Historical decision input."""
    document: dict[str, object] = {
        "source_game_id": snapshot.source_game_id,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_seat": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
        "information_policy": "decision_time",
        "information_cutoff": snapshot.information_cutoff,
        "relative_player_map": snapshot.relative_player_map.copy(),
        "visible_state": _serialize_visible_state(snapshot),
        "effective_review_settings": dict(effective_review_settings),
    }
    if snapshot.source_played_at is not None:
        document["source_played_at"] = snapshot.source_played_at
    if external_profile_application is not None:
        document["external_profile_application"] = dict(
            external_profile_application
        )
    if effective_opponent_policies is not None:
        document["effective_opponent_policies"] = dict(
            effective_opponent_policies
        )
    return document


def _historical_context(
    *,
    stage: str,
    decision_index: int,
    player_id: str | None,
    side: str | None,
) -> InformationUseContext:
    return InformationUseContext(
        workflow="historical_game",
        stage=stage,
        perspective_player_id=player_id,
        perspective_side=side,
        decision_index=decision_index,
        event_index=None,
    )


def _historical_input_entry_builder(
    *,
    snapshot: HistoricalDecisionSnapshot,
    external_reference: str | None,
):
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        local_private = len(tokens) >= 2 and tokens[:2] in {
            ("visible_state", "own_hand"),
            ("visible_state", "known_skat_cards"),
        }
        structural = (
            len(tokens) >= 3
            and tokens[:3] == ("visible_state", "declaration", "matadors")
        )
        legal = len(tokens) >= 2 and tokens[:2] == (
            "visible_state",
            "legal_cards",
        )
        external = tokens and tokens[0] in {
            "external_profile_application",
            "effective_opponent_policies",
        }
        if structural:
            origin = "structural_inference"
            derivation = "exact_aggregate"
            references = (_reference("algorithm", "decision_time_matador_inference"),)
        elif legal:
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (_reference("rule_contract", "legal_card_rules"),)
        elif external:
            origin = "external_source"
            derivation = "validated"
            references = (
                (_reference(
                    "external_record",
                    external_reference,
                    visibility="engine_private",
                ),)
                if external_reference is not None
                else (_reference("algorithm", "historical_profile_application"),)
            )
        elif tokens and tokens[0] == "effective_review_settings":
            origin = "validated_copy"
            derivation = "validated"
            references = (_reference("request", "historical_review_options"),)
        else:
            origin = "historical_replay"
            derivation = "reconstruction"
            references = (_reference("historical_game", snapshot.source_game_id),)
        return _entry(
            path,
            origin=origin,
            visibility="local_private" if local_private else "public",
            available_from="current_decision",
            derivation=derivation,
            decision_index=snapshot.decision_index,
            perspective_player_id=snapshot.acting_player_id,
            source_references=references,
        )

    return build


def build_historical_decision_input_attachment(
    snapshot: HistoricalDecisionSnapshot,
    *,
    effective_review_settings: Mapping[str, object],
    external_profile_application: Mapping[str, object] | None = None,
    effective_opponent_policies: Mapping[str, object] | None = None,
    external_reference: str | None = None,
) -> ApplicationProvenanceAttachment:
    document = build_historical_decision_input_document(
        snapshot,
        effective_review_settings=effective_review_settings,
        external_profile_application=external_profile_application,
        effective_opponent_policies=effective_opponent_policies,
    )
    return build_complete_provenance_attachment(
        name=f"historical_decision/{snapshot.decision_index}/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_historical_context(
            stage="decision_time",
            decision_index=snapshot.decision_index,
            player_id=snapshot.acting_player_id,
            side=snapshot.acting_side,
        ),
        entry_builder=_historical_input_entry_builder(
            snapshot=snapshot,
            external_reference=external_reference,
        ),
    )


def _summary_decision_index(
    document: Mapping[str, object],
    tokens: tuple[str, ...],
    *,
    rows_key: str,
) -> int | None:
    if len(tokens) >= 2 and tokens[0] == rows_key and tokens[1].isdecimal():
        rows = document.get(rows_key)
        if isinstance(rows, (list, tuple)):
            row = rows[int(tokens[1])]
            if isinstance(row, Mapping) and type(row.get("decision_index")) is int:
                return row["decision_index"]
    return None


def _summary_entry_builder(
    *,
    document: Mapping[str, object],
    kind: str,
):
    rows_key = "snapshots" if kind == "snapshot" else "decisions"

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        decision_index = _summary_decision_index(document, tokens, rows_key=rows_key)
        actual = tokens[-1] in {"actual_card", "actual_card_played"}
        if decision_index is not None and actual:
            return _entry(
                path,
                origin="retrospective_attachment",
                visibility="public",
                available_from="after_actual_play",
                derivation="retrospective",
                decision_index=decision_index,
                perspective_player_id=None,
                source_references=(
                    _reference("retrospective_observation", "historical_actual_card"),
                ),
            )
        if decision_index is not None and kind == "snapshot":
            local_private = "own_hand" in tokens or "known_skat_cards" in tokens
            origin = (
                "rule_derived"
                if "legal_cards" in tokens
                else "structural_inference"
                if tokens[-1] == "matadors"
                else "historical_replay"
            )
            derivation = (
                "deterministic_rule"
                if origin == "rule_derived"
                else "exact_aggregate"
                if origin == "structural_inference"
                else "reconstruction"
            )
            row = document[rows_key][int(tokens[1])]
            return _entry(
                path,
                origin=origin,
                visibility="local_private" if local_private else "public",
                available_from="current_decision",
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=row["acting_player_id"],
                source_references=(
                    _reference("historical_game", row["source_game_id"]),
                ),
            )
        if decision_index is not None:
            pre_actual = kind == "search" and (
                "bounded_search_result" in tokens
                or "immediate_baseline" in tokens
                or "search_vs_immediate_comparison" in tokens
            )
            pre_actual = pre_actual or kind == "immediate" and (
                "analysis_report" in tokens
                or "recommendation" in tokens
                or "legal_cards" in tokens
                or "hidden_card_inference_summary" in tokens
                or "opponent_profile_application" in tokens
            )
            available_from = "current_decision" if pre_actual else "after_actual_play"
            return _entry(
                path,
                origin="search_derived" if kind == "search" else "heuristic_analysis",
                visibility="public",
                available_from=available_from,
                derivation="direct" if kind == "search" else "heuristic",
                decision_index=decision_index,
                perspective_player_id=None,
                source_references=(
                    _reference("algorithm", f"historical_{kind}_review"),
                ),
            )
        return _entry(
            path,
            origin="historical_aggregation",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            decision_index=None,
            perspective_player_id=None,
            source_references=(_reference("aggregate", f"historical_{kind}_summary"),),
        )

    return build


def _information_set_summary_entry_builder(
    document: Mapping[str, object],
):
    option_paths = {
        "base_search_seed": "/search_seed",
        "search_budget_profile": "/search_budget_profile",
        "immediate_sample_count": "/immediate_sample_count",
        "immediate_base_random_seed": "/immediate_base_random_seed",
    }

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        decision_index = _summary_decision_index(
            document,
            tokens,
            rows_key="decisions",
        )
        if decision_index is not None:
            row = document["decisions"][int(tokens[1])]
            player_id = row["acting_player_id"]
            field_name = tokens[-1]
            if "actual" in field_name:
                return _entry(
                    path,
                    origin="retrospective_attachment",
                    visibility="public",
                    available_from="after_actual_play",
                    derivation="retrospective",
                    decision_index=decision_index,
                    perspective_player_id=player_id,
                    source_references=(
                        _reference(
                            "retrospective_observation",
                            f"{row['source_game_id']}/{decision_index}",
                        ),
                    ),
                )
            if "information_set_search_result" in tokens:
                reference_id = "bounded_information_set_policy_search_v1"
                origin = "search_derived"
                derivation = "direct"
            elif "same_selection_pimc_result" in tokens:
                reference_id = "compatible_world_minimax_same_selection_v1"
                origin = "search_derived"
                derivation = "direct"
            elif "immediate_baseline" in tokens:
                reference_id = "immediate_expected_value"
                origin = "heuristic_analysis"
                derivation = "heuristic"
            elif "comparison" in tokens:
                reference_id = "information_set_search_comparison_v1"
                origin = "rule_derived"
                derivation = "deterministic_rule"
            else:
                reference_id = str(row["source_game_id"])
                origin = "historical_replay"
                derivation = "reconstruction"
            return _entry(
                path,
                origin=origin,
                visibility="public",
                available_from="current_decision",
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=player_id,
                source_references=(
                    _reference(
                        "historical_game"
                        if origin == "historical_replay"
                        else "rule_contract"
                        if "comparison" in tokens
                        else "algorithm",
                        reference_id,
                    ),
                ),
            )
        if len(tokens) >= 2 and tokens[0] == "settings":
            field_name = tokens[1]
            source_path = option_paths.get(field_name)
            if field_name == "requested_budget":
                return _entry(
                    path,
                    origin="rule_derived",
                    visibility="public",
                    available_from="offline_review",
                    derivation="deterministic_rule",
                    decision_index=None,
                    perspective_player_id=None,
                    source_references=(
                        _reference(
                            "request",
                            "historical_review_options",
                            field_path="/search_budget_profile",
                        ),
                        _reference(
                            "rule_contract",
                            "information_set_budget_profile_conversion_v1",
                        ),
                    ),
                )
            return _entry(
                path,
                origin="validated_copy",
                visibility="public",
                available_from="offline_review",
                derivation="validated",
                decision_index=None,
                perspective_player_id=None,
                source_references=(
                    _reference(
                        "request",
                        "historical_review_options",
                        field_path=source_path,
                    ),
                ),
            )
        return _entry(
            path,
            origin="historical_aggregation",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            decision_index=None,
            perspective_player_id=None,
            source_references=(
                _reference(
                    "aggregate",
                    "historical_information_set_search_review_summary",
                ),
            ),
        )

    return build


def build_historical_summary_attachment(
    *,
    name: str,
    document: Mapping[str, object],
    kind: str,
) -> ApplicationProvenanceAttachment:
    rows = document.get("snapshots" if kind == "snapshot" else "decisions", ())
    max_index = max(
        (
            row.get("decision_index", 0)
            for row in rows
            if isinstance(row, Mapping)
        ),
        default=0,
    )
    return build_complete_provenance_attachment(
        name=name,
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="offline_review",
            decision_index=max_index,
            player_id=None,
            side=None,
        ),
        entry_builder=(
            _information_set_summary_entry_builder(document)
            if kind == "information_set_search"
            else _summary_entry_builder(document=document, kind=kind)
        ),
        validate_entry_use=kind != "snapshot",
    )


def _information_set_coaching_assessment_context(
    document: Mapping[str, object],
    tokens: tuple[str, ...],
) -> tuple[int, str] | None:
    value: object = document
    for token in tokens:
        if isinstance(value, Mapping):
            evidence = value.get("decision_time_evidence")
            if isinstance(evidence, Mapping):
                decision_index = evidence.get("decision_index")
                acting_player_id = evidence.get("acting_player_id")
                if type(decision_index) is int and isinstance(
                    acting_player_id, str
                ):
                    return decision_index, acting_player_id
            value = value.get(token)
        elif isinstance(value, (list, tuple)) and token.isdecimal():
            value = value[int(token)]
        else:
            break
    return None


def _information_set_coaching_report_entry_builder(
    document: Mapping[str, object],
):

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens and tokens[0] == "outcome_context":
            return _entry(
                path,
                origin="rule_derived",
                visibility="post_game_only",
                available_from="game_end",
                derivation="deterministic_rule",
                decision_index=None,
                perspective_player_id=None,
                source_references=(
                    _reference("historical_game", "final_outcome_context"),
                ),
            )
        assessment_context = _information_set_coaching_assessment_context(
            document,
            tokens,
        )
        if assessment_context is not None:
            decision_index, acting_player_id = assessment_context
            if "decision_time_evidence" in tokens:
                if any("immediate" in token for token in tokens):
                    origin = "heuristic_analysis"
                    derivation = "heuristic"
                    references = (
                        _reference("algorithm", "immediate_expected_value"),
                    )
                elif any("pimc" in token for token in tokens):
                    origin = "search_derived"
                    derivation = "direct"
                    references = (
                        _reference(
                            "algorithm",
                            "compatible_world_minimax_same_selection_v1",
                        ),
                    )
                elif tokens[-1] == "same_selected_world_sequence":
                    origin = "rule_derived"
                    derivation = "deterministic_rule"
                    references = (
                        _reference(
                            "aggregate",
                            "retained_historical_information_set_search_review",
                        ),
                        _reference(
                            "algorithm",
                            "compatible_world_minimax_same_selection_v1",
                        ),
                    )
                else:
                    origin = "search_derived"
                    derivation = "direct"
                    references = (
                        _reference(
                            "aggregate",
                            "retained_historical_information_set_search_review",
                        ),
                    )
                return _entry(
                    path,
                    origin=origin,
                    visibility="public",
                    available_from="current_decision",
                    derivation=derivation,
                    decision_index=decision_index,
                    perspective_player_id=acting_player_id,
                    source_references=references,
                )
            if "comparison" in tokens:
                field_name = tokens[-1]
                uses_actual = "actual" in field_name
                references = []
                if "information_set" in field_name:
                    references.append(
                        _reference(
                            "algorithm",
                            "bounded_information_set_policy_search_v1",
                        )
                    )
                if "pimc" in field_name:
                    references.append(
                        _reference(
                            "algorithm",
                            "compatible_world_minimax_same_selection_v1",
                        )
                    )
                if "immediate" in field_name:
                    references.append(
                        _reference("algorithm", "immediate_expected_value")
                    )
                if uses_actual:
                    references.append(
                        _reference(
                            "retrospective_observation",
                            "historical_actual_card",
                        )
                    )
                references.append(
                    _reference(
                        "rule_contract",
                        "information_set_search_comparison_v1",
                    )
                )
                return _entry(
                    path,
                    origin=(
                        "retrospective_attachment"
                        if field_name == "actual_card"
                        else "rule_derived"
                    ),
                    visibility="public",
                    available_from=(
                        "after_actual_play" if uses_actual else "current_decision"
                    ),
                    derivation=(
                        "retrospective"
                        if field_name == "actual_card"
                        else "deterministic_rule"
                    ),
                    decision_index=decision_index,
                    perspective_player_id=acting_player_id,
                    source_references=tuple(dict.fromkeys(references)),
                )
            actual = tokens[-1] == "actual_card"
            return _entry(
                path,
                origin=(
                    "retrospective_attachment" if actual else "rule_derived"
                ),
                visibility="public",
                available_from="after_actual_play",
                derivation="retrospective" if actual else "deterministic_rule",
                decision_index=decision_index,
                perspective_player_id=acting_player_id,
                source_references=(
                    _reference(
                        "retrospective_observation" if actual else "algorithm",
                        (
                            "historical_actual_card"
                            if actual
                            else "information_set_replay_coaching_assessment_v1"
                        ),
                    ),
                ),
            )
        if tokens and tokens[0] == "game_context":
            return _entry(
                path,
                origin="historical_replay",
                visibility="public",
                available_from="game_end",
                derivation="reconstruction",
                decision_index=None,
                perspective_player_id=None,
                source_references=(
                    _reference("historical_game", "coaching_source_game"),
                ),
            )
        if tokens and tokens[0] == "source_review_settings":
            option_paths = {
                "base_search_seed": "/search_seed",
                "search_budget_profile": "/search_budget_profile",
                "requested_budget": "/search_budget_profile",
                "immediate_sample_count": "/immediate_sample_count",
                "immediate_base_random_seed": "/immediate_base_random_seed",
            }
            return _entry(
                path,
                origin="validated_copy",
                visibility="public",
                available_from="offline_review",
                derivation="validated",
                decision_index=None,
                perspective_player_id=None,
                source_references=(
                    _reference(
                        "request",
                        "historical_review_options",
                        field_path=option_paths.get(tokens[1]),
                    ),
                ),
            )
        return _entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="offline_review",
            derivation="deterministic_rule",
            decision_index=None,
            perspective_player_id=None,
            source_references=(
                _reference(
                    "algorithm",
                    "historical_information_set_replay_coaching_v1",
                ),
            ),
        )

    return build


def build_information_set_replay_coaching_report_attachment(
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    """Builds complete provenance over an already serialized safe report."""
    assessments = document.get("assessments")
    if not isinstance(assessments, (list, tuple)):
        assessments = document.get("decision_assessments", ())
    decision_indexes = tuple(
        evidence.get("decision_index", 0)
        for row in assessments
        if isinstance(row, Mapping)
        and isinstance((evidence := row.get("decision_time_evidence")), Mapping)
        and type(evidence.get("decision_index")) is int
    )
    assessment_field = (
        "assessments"
        if isinstance(document.get("assessments"), (list, tuple))
        else "decision_assessments"
    )
    overrides = []
    for index, row in enumerate(assessments):
        if not isinstance(row, Mapping):
            continue
        evidence = row.get("decision_time_evidence")
        comparison = row.get("comparison")
        if not isinstance(evidence, Mapping) or not isinstance(comparison, Mapping):
            continue
        decision_index = evidence.get("decision_index")
        source_game_id = evidence.get("source_game_id")
        acting_player_id = evidence.get("acting_player_id")
        if (
            type(decision_index) is not int
            or not isinstance(source_game_id, str)
            or not isinstance(acting_player_id, str)
        ):
            continue
        overrides.extend(
            build_information_set_search_comparison_provenance_entries(
                comparison,
                field_path=f"/{assessment_field}/{index}/comparison",
                decision_index=decision_index,
                perspective_player_id=acting_player_id,
                actual_reference_id=f"{source_game_id}/{decision_index}",
            )
        )
    return build_complete_provenance_attachment(
        name="information_set_replay_coaching/report",
        document_role="result",
        document=document,
        information_use_context=_historical_context(
            stage="offline_review",
            decision_index=max(decision_indexes, default=0),
            player_id=None,
            side=None,
        ),
        entry_builder=_information_set_coaching_report_entry_builder(document),
        override_entries=tuple(overrides),
    )


def build_historical_game_result_attachment(
    result: Mapping[str, object],
    *,
    external_reference: str | None,
    source_document: Mapping[str, object] | None = None,
) -> ApplicationProvenanceAttachment:
    """Builds complete provenance while preserving the historical import seam."""
    return _build_complete_historical_game_result_attachment(
        result,
        source_document=source_document,
        external_reference=external_reference,
    )


class HistoricalReviewProvenanceCollector:
    """Collects retained Historical Review and Replay Coaching stage values."""

    def __init__(self, *, external_reference: str | None) -> None:
        self._external_reference = external_reference
        self._snapshots: dict[int, HistoricalDecisionSnapshot] = {}
        self._settings: dict[int, dict[str, object]] = {}
        self._profile_applications: dict[int, dict[str, object]] = {}
        self._effective_policies: dict[int, dict[str, object]] = {}
        self._analysis_documents: dict[int, dict[str, object]] = {}
        self._assessment_documents: dict[int, dict[str, object]] = {}
        self._search_evidence: dict[int, DecisionTimeReplayCoachingEvidence] = {}
        self._coaching_assessments: dict[int, object] = {}
        self._aggregate_attachments: list[ApplicationProvenanceAttachment] = []

    def capture_decision_inputs(
        self,
        snapshot_summary: HistoricalDecisionSnapshotSummary,
        *,
        effective_review_settings: Mapping[str, object],
    ) -> None:
        for snapshot in snapshot_summary.snapshots:
            self._snapshots[snapshot.decision_index] = snapshot
            self._settings[snapshot.decision_index] = dict(effective_review_settings)
            self._validate_input(snapshot.decision_index)

    def _validate_input(self, decision_index: int) -> ApplicationProvenanceAttachment:
        snapshot = self._snapshots[decision_index]
        return build_historical_decision_input_attachment(
            snapshot,
            effective_review_settings=self._settings[decision_index],
            external_profile_application=self._profile_applications.get(decision_index),
            effective_opponent_policies=self._effective_policies.get(decision_index),
            external_reference=self._external_reference,
        )

    def capture_profile_application(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        external_profile_application: Mapping[str, object],
        effective_opponent_policies: Mapping[str, object],
    ) -> None:
        self._profile_applications[snapshot.decision_index] = dict(
            external_profile_application
        )
        self._effective_policies[snapshot.decision_index] = dict(
            effective_opponent_policies
        )
        self._validate_input(snapshot.decision_index)

    def capture_information_set_search_policy_settings(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        effective_settings: EffectiveOpponentPolicySettings,
    ) -> None:
        if not isinstance(effective_settings, EffectiveOpponentPolicySettings):
            raise ValueError("Effective Information-set policy settings have the wrong type.")
        self._effective_policies[snapshot.decision_index] = {
            "left": {
                "lead_policy": effective_settings.left_lead_policy,
                "response_policy": effective_settings.left_response_policy,
            },
            "right": {
                "lead_policy": effective_settings.right_lead_policy,
                "response_policy": effective_settings.right_response_policy,
            },
        }
        self._validate_input(snapshot.decision_index)

    def capture_immediate_analysis(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        document: Mapping[str, object],
    ) -> None:
        validate_retrospective_provenance_dependency(
            consumer_stage="decision_time_analysis",
            dependency_stage="decision_input",
            path=f"/historical_decision/{snapshot.decision_index}/analysis",
        )
        self._analysis_documents.setdefault(snapshot.decision_index, {})[
            "immediate_review"
        ] = dict(document)

    def capture_immediate_assessment(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        document: Mapping[str, object],
    ) -> None:
        self._assessment_documents.setdefault(snapshot.decision_index, {})[
            "immediate_review"
        ] = dict(document)

    def capture_search_analysis(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        analysis: HistoricalSearchDecisionPreActualAnalysis,
    ) -> None:
        evidence = analysis.decision_time_evidence
        self._search_evidence[snapshot.decision_index] = evidence
        self._analysis_documents.setdefault(snapshot.decision_index, {})[
            "historical_search_review"
        ] = {
            "remaining_tricks": analysis.remaining_tricks,
            "legal_cards": list(analysis.position.legal_cards),
            "public_hand_constraints": build_serializable_public_hand_constraints(
                analysis.position.public_hand_constraints
            ),
            "immediate_recommendation": {
                "card": analysis.immediate_card,
                "reason": analysis.immediate_reason,
            },
            "immediate_analysis_report": [
                dict(row) for row in analysis.immediate_report
            ],
            "decision_time_evidence": (
                build_serializable_decision_time_replay_coaching_evidence(evidence)
            ),
        }

    def capture_search_assessment(
        self,
        *,
        snapshot: HistoricalDecisionSnapshot,
        attachment: HistoricalSearchDecisionRetrospectiveAttachment,
    ) -> None:
        self._coaching_assessments[snapshot.decision_index] = (
            attachment.coaching_assessment
        )
        self._assessment_documents.setdefault(snapshot.decision_index, {})[
            "historical_search_review"
        ] = {
            "actual_card": snapshot.actual_card_played,
            "search_actual_card_comparison": (
                build_serializable_search_actual_card_comparison(
                    attachment.search_actual_card_comparison
                )
            ),
            "replay_coaching_assessment": (
                build_serializable_replay_coaching_decision_assessment(
                    attachment.coaching_assessment
                )
            ),
        }

    def capture_snapshot_summary(self, document: Mapping[str, object]) -> None:
        self._aggregate_attachments.append(
            build_historical_summary_attachment(
                name="historical_snapshot_summary",
                document=document,
                kind="snapshot",
            )
        )

    def capture_immediate_summary(self, document: Mapping[str, object]) -> None:
        self._aggregate_attachments.append(
            build_historical_summary_attachment(
                name="historical_immediate_review_summary",
                document=document,
                kind="immediate",
            )
        )

    def capture_search_summary(self, document: Mapping[str, object]) -> None:
        self._aggregate_attachments.append(
            build_historical_summary_attachment(
                name="historical_search_review_summary",
                document=document,
                kind="search",
            )
        )

    def capture_information_set_search_summary(
        self,
        document: Mapping[str, object],
    ) -> None:
        decisions = document.get("decisions", ())
        if not isinstance(decisions, (list, tuple)):
            raise ValueError("Information-set Historical summary requires decisions.")
        for decision in decisions:
            if not isinstance(decision, Mapping):
                raise ValueError("Information-set Historical decisions must be objects.")
            decision_index = decision.get("decision_index")
            if type(decision_index) is not int or decision_index not in self._snapshots:
                raise ValueError(
                    "Information-set Historical decisions must match captured snapshots."
                )
            self._analysis_documents.setdefault(decision_index, {})[
                "historical_information_set_search_review"
            ] = {
                "information_set_search_result": decision.get(
                    "information_set_search_result"
                ),
                "same_selection_pimc_result": decision.get(
                    "same_selection_pimc_result"
                ),
                "immediate_baseline": decision.get("immediate_baseline"),
            }
            self._assessment_documents.setdefault(decision_index, {})[
                "historical_information_set_search_review"
            ] = {
                "actual_card": decision.get("actual_card"),
                "comparison": decision.get("comparison"),
            }
        self._aggregate_attachments.append(
            build_historical_summary_attachment(
                name="historical_information_set_search_review_summary",
                document=document,
                kind="information_set_search",
            )
        )

    def capture_information_set_replay_coaching_report(
        self,
        document: Mapping[str, object],
    ) -> None:
        self._aggregate_attachments.append(
            build_information_set_replay_coaching_report_attachment(document)
        )

    def capture_prioritization(
        self,
        result: ReplayCoachingPrioritizationResult,
    ) -> None:
        self._aggregate_attachments.append(
            build_replay_coaching_prioritization_attachment(result)
        )

    def capture_guidance(self, result: ReplayCoachingGuidanceResult) -> None:
        self._aggregate_attachments.append(
            build_replay_coaching_guidance_attachment(result)
        )

    def capture_report(self, report: ReplayCoachingReport) -> None:
        self._aggregate_attachments.append(
            build_replay_coaching_report_attachment(report)
        )

    def _build_analysis_attachment(
        self,
        decision_index: int,
    ) -> ApplicationProvenanceAttachment:
        snapshot = self._snapshots[decision_index]
        document = self._analysis_documents[decision_index]
        evidence = self._search_evidence.get(decision_index)

        def builder(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
            origin = (
                "search_derived"
                if tokens and tokens[0] == "historical_search_review"
                else "structural_inference"
                if "hidden_card_inference_summary" in tokens
                else "heuristic_analysis"
            )
            derivation = (
                "direct"
                if origin == "search_derived"
                else "exact_aggregate"
                if origin == "structural_inference"
                else "heuristic"
            )
            return _entry(
                path,
                origin=origin,
                visibility="public",
                available_from="current_decision",
                derivation=derivation,
                decision_index=decision_index,
                perspective_player_id=snapshot.acting_player_id,
                source_references=(
                    _reference("algorithm", "historical_decision_analysis"),
                ),
            )

        overrides: tuple[FieldProvenanceEntry, ...] = ()
        if evidence is not None:
            overrides = search_entries_for_nested_result(
                evidence.bounded_search_result,
                field_path=(
                    "/historical_search_review/decision_time_evidence/"
                    "bounded_search_result"
                ),
                decision_index=decision_index,
                perspective_player_id=snapshot.acting_player_id,
            )
        information_set_review = document.get(
            "historical_information_set_search_review"
        )
        if isinstance(information_set_review, Mapping):
            information_entries: list[FieldProvenanceEntry] = list(overrides)
            information_result = information_set_review.get(
                "information_set_search_result"
            )
            information_prefix = (
                "/historical_information_set_search_review/"
                "information_set_search_result"
            )
            if isinstance(information_result, Mapping):
                information_entries.extend(
                    build_information_set_search_provenance_entries(
                        information_result,
                        retained_result=None,
                        field_path=information_prefix,
                        decision_index=decision_index,
                        perspective_player_id=snapshot.acting_player_id,
                        settings_reference=information_set_settings_reference(
                            "request",
                            "historical_review_options",
                            field_path="/search_budget_profile",
                        ),
                        fixed_policy_reference=information_set_settings_reference(
                            "algorithm",
                            "historical_effective_opponent_policy",
                        ),
                    )
                )
            else:
                information_entries.append(
                    _entry(
                        information_prefix,
                        origin="search_derived",
                        visibility="public",
                        available_from="current_decision",
                        derivation="direct",
                        decision_index=decision_index,
                        perspective_player_id=snapshot.acting_player_id,
                        source_references=(
                            _reference(
                                "algorithm",
                                "bounded_information_set_policy_search_v1",
                            ),
                        ),
                    )
                )
            pimc_result = information_set_review.get(
                "same_selection_pimc_result"
            )
            pimc_prefix = (
                "/historical_information_set_search_review/"
                "same_selection_pimc_result"
            )
            if isinstance(pimc_result, Mapping):
                information_entries.extend(
                    build_serialized_pimc_provenance_entries(
                        pimc_result,
                        field_path=pimc_prefix,
                        decision_index=decision_index,
                        perspective_player_id=snapshot.acting_player_id,
                        settings_reference=information_set_settings_reference(
                            "request",
                            "historical_review_options",
                            field_path="/search_budget_profile",
                        ),
                    )
                )
            else:
                information_entries.append(
                    _entry(
                        pimc_prefix,
                        origin="search_derived",
                        visibility="public",
                        available_from="current_decision",
                        derivation="direct",
                        decision_index=decision_index,
                        perspective_player_id=snapshot.acting_player_id,
                        source_references=(
                            _reference(
                                "algorithm",
                                "compatible_world_minimax_same_selection_v1",
                            ),
                        ),
                    )
                )
            immediate = information_set_review.get("immediate_baseline")
            if isinstance(immediate, Mapping):
                for relative_path in enumerate_json_leaf_paths(immediate):
                    information_entries.append(
                        _entry(
                            (
                                "/historical_information_set_search_review/"
                                f"immediate_baseline{relative_path}"
                            ),
                            origin="heuristic_analysis",
                            visibility="public",
                            available_from="current_decision",
                            derivation="heuristic",
                            decision_index=decision_index,
                            perspective_player_id=snapshot.acting_player_id,
                            source_references=(
                                _reference(
                                    "algorithm",
                                    "immediate_expected_value",
                                ),
                            ),
                        )
                    )
            overrides = tuple(information_entries)
        return build_complete_provenance_attachment(
            name=f"historical_decision/{decision_index}/analysis",
            document_role="result",
            document=document,
            information_use_context=_historical_context(
                stage="decision_time",
                decision_index=decision_index,
                player_id=snapshot.acting_player_id,
                side=snapshot.acting_side,
            ),
            entry_builder=builder,
            override_entries=overrides,
        )

    def _build_assessment_attachment(
        self,
        decision_index: int,
    ) -> ApplicationProvenanceAttachment:
        snapshot = self._snapshots[decision_index]
        document = self._assessment_documents[decision_index]

        def builder(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
            in_decision_evidence = "decision_time_evidence" in tokens
            is_actual = tokens[-1] in {"actual_card", "actual_card_played"}
            return _entry(
                path,
                origin=(
                    "search_derived"
                    if in_decision_evidence
                    else "retrospective_attachment"
                    if is_actual
                    else "heuristic_analysis"
                ),
                visibility="public",
                available_from=(
                    "current_decision" if in_decision_evidence else "after_actual_play"
                ),
                derivation=(
                    "direct"
                    if in_decision_evidence
                    else "retrospective"
                    if is_actual
                    else "heuristic"
                ),
                decision_index=decision_index,
                perspective_player_id=snapshot.acting_player_id,
                source_references=(
                    _reference(
                        "retrospective_observation" if is_actual else "algorithm",
                        "historical_actual_card" if is_actual else "historical_assessment",
                    ),
                ),
            )

        overrides: tuple[FieldProvenanceEntry, ...] = ()
        coaching = self._coaching_assessments.get(decision_index)
        if coaching is not None:
            overrides = search_entries_for_nested_result(
                coaching.decision_time_evidence.bounded_search_result,
                field_path=(
                    "/historical_search_review/replay_coaching_assessment/"
                    "decision_time_evidence/bounded_search_result"
                ),
                decision_index=decision_index,
                perspective_player_id=snapshot.acting_player_id,
            )
        information_set_review = document.get(
            "historical_information_set_search_review"
        )
        if isinstance(information_set_review, Mapping):
            comparison = information_set_review.get("comparison")
            if isinstance(comparison, Mapping):
                overrides = (
                    *overrides,
                    *build_information_set_search_comparison_provenance_entries(
                        comparison,
                        field_path=(
                            "/historical_information_set_search_review/comparison"
                        ),
                        decision_index=decision_index,
                        perspective_player_id=snapshot.acting_player_id,
                        actual_reference_id=(
                            f"{snapshot.source_game_id}/{decision_index}"
                        ),
                    ),
                )
        return build_complete_provenance_attachment(
            name=f"historical_decision/{decision_index}/assessment",
            document_role="result",
            document=document,
            information_use_context=_historical_context(
                stage="after_actual_play",
                decision_index=decision_index,
                player_id=snapshot.acting_player_id,
                side=snapshot.acting_side,
            ),
            entry_builder=builder,
            override_entries=overrides,
        )

    def build_bundle(
        self,
        result: Mapping[str, object],
        *,
        source_document: Mapping[str, object] | None = None,
    ) -> ApplicationProvenanceBundle:
        attachments: list[ApplicationProvenanceAttachment] = []
        for decision_index in sorted(self._snapshots):
            attachments.append(self._validate_input(decision_index))
            if decision_index in self._analysis_documents:
                attachments.append(self._build_analysis_attachment(decision_index))
            if decision_index in self._assessment_documents:
                attachments.append(self._build_assessment_attachment(decision_index))
        attachments.extend(self._aggregate_attachments)
        attachments.append(
            build_historical_game_result_attachment(
                result,
                external_reference=self._external_reference,
                source_document=source_document,
            )
        )
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.HISTORICAL_GAME,
            attachments=tuple(attachments),
        )
