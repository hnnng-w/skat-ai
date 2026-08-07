from __future__ import annotations

from collections.abc import Mapping

from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.application.contracts import ApplicationArtifact, TrainingDatasetApplicationOptions
from skat_ai.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skat_ai.field_provenance import FieldProvenanceEntry, FieldProvenanceSourceReference
from skat_ai.field_provenance_coverage import enumerate_json_leaf_paths
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
)
from skat_ai.training_dataset import (
    TrainingDatasetInput,
    build_serializable_training_dataset_input,
)

TRAINING_DATASET_PROVENANCE_VERSION = 1


def _context(
    stage: str,
    *,
    player_id: str | None = None,
    side: str | None = None,
    decision_index: int | None = None,
) -> InformationUseContext:
    return InformationUseContext(
        workflow="training_dataset",
        stage=stage,
        perspective_player_id=player_id,
        perspective_side=side,
        decision_index=decision_index,
        event_index=None,
    )


def _source_reference(record_index: int) -> FieldProvenanceSourceReference:
    return _reference("external_record", f"training_dataset_record/{record_index}")


def _offline_entry_builder(
    reference: FieldProvenanceSourceReference,
    *,
    origin: str = "historical_aggregation",
    derivation: str = "exact_aggregate",
):
    def build(path: str, _tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        return _entry(
            path,
            origin=origin,
            visibility="public",
            available_from="offline_review",
            derivation=derivation,
            decision_index=None,
            perspective_player_id=None,
            source_references=(reference,),
        )

    return build


def _fixed_entry_builder(
    *,
    origin: str,
    visibility: str,
    available_from: str,
    derivation: str,
    decision_index: int,
    player_id: str,
    references: tuple[FieldProvenanceSourceReference, ...],
):
    def build(path: str, _tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        return _entry(
            path,
            origin=origin,
            visibility=visibility,
            available_from=available_from,
            derivation=derivation,
            decision_index=decision_index,
            perspective_player_id=player_id,
            source_references=references,
        )

    return build


def _build_dataset_input_attachment(
    dataset: TrainingDatasetInput,
) -> ApplicationProvenanceAttachment:
    document = build_serializable_training_dataset_input(dataset)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        record_index = (
            int(tokens[1])
            if len(tokens) >= 2 and tokens[0] == "records" and tokens[1].isdecimal()
            else None
        )
        if record_index is None:
            origin = "validated_copy"
            references = (_reference("request", "training_dataset_input"),)
        else:
            origin = "external_source"
            references = (_source_reference(record_index),)
        return _entry(
            path,
            origin=origin,
            visibility="post_game_only",
            available_from="offline_review",
            derivation="validated",
            decision_index=None,
            perspective_player_id=None,
            source_references=references,
        )

    return build_complete_provenance_attachment(
        name="training_dataset/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_context("offline_review"),
        entry_builder=build,
    )


def _build_record_attachment(
    dataset_document: Mapping[str, object],
    record_index: int,
) -> ApplicationProvenanceAttachment:
    records = dataset_document["records"]
    assert isinstance(records, list)
    document = records[record_index]
    assert isinstance(document, Mapping)
    return build_complete_provenance_attachment(
        name=f"training_dataset/record/{record_index}",
        document_role="consumed_input",
        document=document,
        information_use_context=_context("offline_review"),
        entry_builder=_offline_entry_builder(
            _source_reference(record_index),
            origin="external_source",
            derivation="validated",
        ),
    )


def _build_feature_attachment(
    *,
    record_index: int,
    decision_index: int,
    game_id: str,
    player_id: str,
    side: str,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    game_reference = _reference("historical_game", game_id)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        root = tokens[0] if tokens else ""
        local_private = root in {"own_hand", "known_skat_cards"}
        if root == "legal_cards":
            origin = "rule_derived"
            derivation = "deterministic_rule"
            references = (_reference("rule_contract", "legal_card_rules"),)
        elif tokens[:2] == ("declaration", "matadors"):
            origin = "structural_inference"
            derivation = "exact_aggregate"
            references = (_reference("algorithm", "decision_time_matador_inference"),)
        else:
            origin = "historical_replay"
            derivation = "reconstruction"
            references = (game_reference,)
        return _entry(
            path,
            origin=origin,
            visibility="local_private" if local_private else "public",
            available_from="current_decision",
            derivation=derivation,
            decision_index=decision_index,
            perspective_player_id=player_id,
            source_references=references,
        )

    return build_complete_provenance_attachment(
        name=f"training_dataset/sample/{record_index}/{decision_index}/feature",
        document_role="result",
        document=document,
        information_use_context=_context(
            "decision_time",
            player_id=player_id,
            side=side,
            decision_index=decision_index,
        ),
        entry_builder=build,
    )


def _build_target_attachment(
    *,
    record_index: int,
    decision_index: int,
    game_id: str,
    player_id: str,
    side: str,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    def build(path: str, _tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        return _entry(
            path,
            origin="retrospective_attachment",
            visibility="public",
            available_from="after_actual_play",
            derivation="retrospective",
            decision_index=decision_index,
            perspective_player_id=player_id,
            source_references=(
                _reference("retrospective_observation", f"{game_id}/{decision_index}"),
            ),
        )

    return build_complete_provenance_attachment(
        name=f"training_dataset/sample/{record_index}/{decision_index}/target",
        document_role="result",
        document=document,
        information_use_context=_context(
            "after_actual_play",
            player_id=player_id,
            side=side,
            decision_index=decision_index,
        ),
        entry_builder=build,
    )


def _rolling_prediction_document(decision: Mapping[str, object]) -> dict[str, object]:
    result = {
        key: decision[key]
        for key in (
            "game_id",
            "decision_index",
            "trick_number",
            "play_index",
            "acting_player_id",
            "acting_side",
            "game_type",
            "decision_phase",
            "legal_cards",
            "profile_history_status",
            "profile_prediction_status",
            "profile_derivation_status",
            "overall_profile_confidence",
            "relevant_role_confidence",
            "actionable_profile_preset",
            "profile_prediction_unavailable_reason",
        )
    }
    for key in ("baseline_prediction", "profile_prediction"):
        prediction = decision[key]
        if prediction is None:
            result[key] = None
            continue
        assert isinstance(prediction, Mapping)
        result[key] = {
            field: prediction[field]
            for field in (
                "policy_preset",
                "concrete_policy",
                "decision_phase",
                "predicted_card",
                "preferred_cards",
            )
        }
    return result


def _rolling_actual_document(decision: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {
        "actual_card": decision["actual_card"],
        "preferred_comparison_outcome": decision["preferred_comparison_outcome"],
        "exact_comparison_outcome": decision["exact_comparison_outcome"],
    }
    for key in ("baseline_prediction", "profile_prediction"):
        prediction = decision[key]
        if prediction is None:
            result[key] = None
            continue
        assert isinstance(prediction, Mapping)
        result[key] = {
            "actual_card": prediction["actual_card"],
            "exact_card_match": prediction["exact_card_match"],
            "preferred_card_match": prediction["preferred_card_match"],
        }
    return result


def _rolling_attachments(
    summary: Mapping[str, object],
) -> list[ApplicationProvenanceAttachment]:
    attachments: list[ApplicationProvenanceAttachment] = []
    target_games = summary["target_games"]
    assert isinstance(target_games, list)
    for target_index, target in enumerate(target_games):
        assert isinstance(target, Mapping)
        profiles = target["player_as_of_profiles"]
        assert isinstance(profiles, list)
        sources_by_player = {
            profile["player_id"]: tuple(profile["source_record_ids"])
            for profile in profiles
            if isinstance(profile, Mapping)
        }
        decisions = target["decisions"]
        assert isinstance(decisions, list)
        for decision in decisions:
            assert isinstance(decision, Mapping)
            decision_index = int(decision["decision_index"])
            player_id = str(decision["acting_player_id"])
            side = str(decision["acting_side"])
            source_references = tuple(
                _reference("external_record", source_id)
                for source_id in sources_by_player.get(player_id, ())
            ) or (_reference("algorithm", "baseline_opponent_policy"),)

            def prediction_entry(
                path: str,
                tokens: tuple[str, ...],
                *,
                references: tuple[FieldProvenanceSourceReference, ...] = source_references,
                current_decision_index: int = decision_index,
                current_player_id: str = player_id,
            ) -> FieldProvenanceEntry:
                profile_value = bool(tokens and tokens[0].startswith("profile_")) or (
                    tokens and tokens[0] == "actionable_profile_preset"
                )
                return _entry(
                    path,
                    origin="heuristic_analysis",
                    visibility=(
                        "local_private" if tokens and tokens[0] == "legal_cards" else "public"
                    ),
                    available_from="current_decision",
                    derivation="heuristic",
                    decision_index=current_decision_index,
                    perspective_player_id=current_player_id,
                    source_references=(
                        references
                        if profile_value
                        else (_reference("algorithm", "baseline_opponent_policy"),)
                    ),
                )

            attachments.append(
                build_complete_provenance_attachment(
                    name=(f"training_dataset/rolling/{target_index}/{decision_index}/prediction"),
                    document_role="result",
                    document=_rolling_prediction_document(decision),
                    information_use_context=_context(
                        "decision_time",
                        player_id=player_id,
                        side=side,
                        decision_index=decision_index,
                    ),
                    entry_builder=prediction_entry,
                )
            )
            attachments.append(
                build_complete_provenance_attachment(
                    name=f"training_dataset/rolling/{target_index}/{decision_index}/actual",
                    document_role="result",
                    document=_rolling_actual_document(decision),
                    information_use_context=_context(
                        "after_actual_play",
                        player_id=player_id,
                        side=side,
                        decision_index=decision_index,
                    ),
                    entry_builder=_fixed_entry_builder(
                        origin="retrospective_attachment",
                        visibility="public",
                        available_from="after_actual_play",
                        derivation="retrospective",
                        decision_index=decision_index,
                        player_id=player_id,
                        references=(
                            _reference(
                                "retrospective_observation",
                                f"{target['game_id']}/{decision_index}",
                            ),
                        ),
                    ),
                )
            )
    return attachments


def _search_input_document(decision: Mapping[str, object]) -> dict[str, object]:
    result = {
        key: decision[key]
        for key in (
            "source_game_id",
            "decision_index",
            "trick_number",
            "play_index",
            "acting_player_id",
            "acting_seat",
            "acting_side",
            "game_type",
            "local_side",
            "root_seat",
            "remaining_tricks",
        )
    }
    if "source_played_at" in decision:
        result["source_played_at"] = decision["source_played_at"]
    baseline = decision["immediate_baseline"]
    assert isinstance(baseline, Mapping)
    result["legal_cards"] = baseline["legal_cards"]
    return result


def _search_result_entry_builder(
    document: Mapping[str, object],
    *,
    decision_index: int,
    player_id: str,
):
    leaf_paths = set(enumerate_json_leaf_paths(document))
    consumed_budget = document["consumed_budget"]
    assert isinstance(consumed_budget, Mapping)
    completed_world_count = consumed_budget["completed_world_count"]
    world_coverage = document["world_coverage"]
    search_reference = _reference("algorithm", str(document["search_method"]))

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        origin = "search_derived"
        derivation = "direct"
        dependencies: tuple[str, ...] = ()
        if tokens and tokens[0] == "requested_budget":
            origin = "validated_copy"
            derivation = "validated"
        elif (
            tokens == ("compatible_world_count",) and document["compatible_world_count"] is not None
        ):
            origin = "compatible_world_aggregate"
            derivation = "exact_aggregate"
        elif len(tokens) >= 3 and tokens[0] == "candidate_results":
            metric = tokens[2]
            if metric in {
                "completed_world_count",
                "local_contract_success_count",
                "local_contract_success_rate",
                "mean_local_side_game_score",
                "mean_local_side_card_point_margin",
            }:
                if completed_world_count == 0:
                    origin = "search_derived"
                    derivation = "direct"
                else:
                    origin = "compatible_world_aggregate"
                    derivation = (
                        "sampled_aggregate"
                        if world_coverage == "sampled_compatible_worlds"
                        else "exact_aggregate"
                    )
            elif metric == "rank":
                dependencies = tuple(
                    sorted(
                        candidate_path
                        for candidate_path in leaf_paths
                        if (
                            candidate_path.startswith("/candidate_results/")
                            and candidate_path.rsplit("/", 1)[-1]
                            in {
                                "card",
                                "local_contract_success_rate",
                                "mean_local_side_game_score",
                                "mean_local_side_card_point_margin",
                            }
                        )
                        or candidate_path == "/game_type"
                    )
                )
                derivation = "deterministic_rule"
            elif metric == "is_recommended":
                rank_path = f"/candidate_results/{tokens[1]}/rank"
                if rank_path in leaf_paths:
                    dependencies = (rank_path,)
                derivation = "deterministic_rule"
        elif tokens == ("recommended_card",):
            dependencies = tuple(
                sorted(
                    candidate_path
                    for candidate_path in leaf_paths
                    if candidate_path.startswith("/candidate_results/")
                    and candidate_path.endswith("/is_recommended")
                )
            )
            derivation = "deterministic_rule" if dependencies else "direct"
        return _entry(
            path,
            origin=origin,
            visibility="public",
            available_from="current_decision",
            derivation=derivation,
            decision_index=decision_index,
            perspective_player_id=player_id,
            source_references=(search_reference,),
            dependency_paths=dependencies,
        )

    return build


def _search_attachments(
    summary: Mapping[str, object],
) -> list[ApplicationProvenanceAttachment]:
    attachments: list[ApplicationProvenanceAttachment] = []
    records = summary["records"]
    assert isinstance(records, list)
    for record_index, record in enumerate(records):
        assert isinstance(record, Mapping)
        decisions = record["decisions"]
        assert isinstance(decisions, list)
        for decision in decisions:
            assert isinstance(decision, Mapping)
            decision_index = int(decision["decision_index"])
            player_id = str(decision["acting_player_id"])
            side = str(decision["acting_side"])
            game_id = str(decision["source_game_id"])
            decision_context = _context(
                "decision_time",
                player_id=player_id,
                side=side,
                decision_index=decision_index,
            )
            stage_documents: tuple[tuple[str, Mapping[str, object]], ...] = (
                ("input", _search_input_document(decision)),
                (
                    "immediate",
                    {
                        key: value
                        for key, value in decision["immediate_baseline"].items()
                        if key != "effective_random_seed"
                    },
                ),
                ("search", decision["bounded_search_result"]),
                ("comparison", decision["search_vs_immediate_comparison"]),
            )
            for stage, document in stage_documents:
                origin = (
                    "historical_replay"
                    if stage == "input"
                    else "heuristic_analysis"
                    if stage == "immediate"
                    else "search_derived"
                )
                derivation = "reconstruction" if stage == "input" else "heuristic"
                entry_builder = (
                    _search_result_entry_builder(
                        document,
                        decision_index=decision_index,
                        player_id=player_id,
                    )
                    if stage == "search"
                    else _fixed_entry_builder(
                        origin=origin,
                        visibility="public",
                        available_from="current_decision",
                        derivation=derivation,
                        decision_index=decision_index,
                        player_id=player_id,
                        references=(
                            _reference(
                                "historical_game" if stage == "input" else "algorithm",
                                game_id if stage == "input" else f"bounded_search_{stage}",
                            ),
                        ),
                    )
                )
                attachments.append(
                    build_complete_provenance_attachment(
                        name=(f"training_dataset/search/{record_index}/{decision_index}/{stage}"),
                        document_role="result",
                        document=document,
                        information_use_context=decision_context,
                        entry_builder=entry_builder,
                    )
                )
            attachments.append(
                build_complete_provenance_attachment(
                    name=f"training_dataset/search/{record_index}/{decision_index}/actual",
                    document_role="result",
                    document={"actual_card": decision["actual_card"]},
                    information_use_context=_context(
                        "after_actual_play",
                        player_id=player_id,
                        side=side,
                        decision_index=decision_index,
                    ),
                    entry_builder=_fixed_entry_builder(
                        origin="retrospective_attachment",
                        visibility="public",
                        available_from="after_actual_play",
                        derivation="retrospective",
                        decision_index=decision_index,
                        player_id=player_id,
                        references=(
                            _reference(
                                "retrospective_observation",
                                f"{game_id}/{decision_index}",
                            ),
                        ),
                    ),
                )
            )
            retrospective = decision["search_actual_card_comparison"]
            assert isinstance(retrospective, Mapping)
            attachments.append(
                build_complete_provenance_attachment(
                    name=(f"training_dataset/search/{record_index}/{decision_index}/retrospective"),
                    document_role="result",
                    document=retrospective,
                    information_use_context=_context(
                        "after_actual_play",
                        player_id=player_id,
                        side=side,
                        decision_index=decision_index,
                    ),
                    entry_builder=_fixed_entry_builder(
                        origin="retrospective_attachment",
                        visibility="public",
                        available_from="after_actual_play",
                        derivation="retrospective",
                        decision_index=decision_index,
                        player_id=player_id,
                        references=(
                            _reference("algorithm", "retrospective_search_comparison"),
                            _reference(
                                "retrospective_observation",
                                f"{game_id}/{decision_index}",
                            ),
                        ),
                    ),
                )
            )
    return attachments


def _operation_entry_builder(operation: str, summary: Mapping[str, object]):
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        origin = "historical_aggregation"
        derivation = "exact_aggregate"
        availability = "offline_review"
        decision_index: int | None = None
        visibility = "post_game_only"
        perspective_player_id: str | None = None
        dependencies: tuple[str, ...] = ()
        references: tuple[FieldProvenanceSourceReference, ...] = (
            _reference("algorithm", f"training_dataset_{operation}"),
        )

        if operation == "summary" and len(tokens) >= 4 and tokens[0] == "records":
            record_index = int(tokens[1])
            if tokens[2] == "samples" and tokens[3].isdecimal():
                sample = summary["records"][record_index]["samples"][int(tokens[3])]
                decision_index = int(sample["metadata"]["decision_index"])
                perspective_player_id = str(sample["metadata"]["acting_player_id"])
                if len(tokens) >= 5 and tokens[4] == "features":
                    origin = "historical_replay"
                    derivation = "reconstruction"
                    availability = "current_decision"
                    visibility = (
                        "local_private"
                        if len(tokens) >= 6 and tokens[5] in {"own_hand", "known_skat_cards"}
                        else "public"
                    )
                    references = (
                        _reference(
                            "aggregate",
                            f"training_feature/{record_index}/{decision_index}",
                        ),
                    )
                elif len(tokens) >= 5 and tokens[4] == "label":
                    origin = "retrospective_attachment"
                    derivation = "retrospective"
                    availability = "after_actual_play"
                    visibility = "public"
                    references = (
                        _reference(
                            "retrospective_observation",
                            f"training_target/{record_index}/{decision_index}",
                        ),
                    )
            elif tokens[2] == "historical_game":
                origin = "external_source"
                derivation = "validated"
                availability = "game_end"
                references = (_source_reference(record_index),)
            else:
                references = (_source_reference(record_index),)
        elif operation == "rolling_opponent_policy_evaluation":
            actual_names = {
                "actual_card",
                "exact_card_match",
                "preferred_card_match",
                "preferred_comparison_outcome",
                "exact_comparison_outcome",
            }
            if actual_names.intersection(tokens):
                origin = "retrospective_attachment"
                derivation = "retrospective"
                availability = "after_actual_play" if "decisions" in tokens else "offline_review"
                visibility = "public" if availability == "after_actual_play" else visibility
                if "decisions" in tokens:
                    decision_position = tokens.index("decisions")
                    target_index = int(tokens[1]) if tokens[0] == "target_games" else 0
                    decision = summary["target_games"][target_index]["decisions"][
                        int(tokens[decision_position + 1])
                    ]
                    decision_index = int(decision["decision_index"])
            elif "decisions" in tokens:
                origin = "heuristic_analysis"
                derivation = "heuristic"
                availability = "current_decision"
                visibility = "public"
                target_index = int(tokens[1])
                decision_position = tokens.index("decisions")
                decision = summary["target_games"][target_index]["decisions"][
                    int(tokens[decision_position + 1])
                ]
                decision_index = int(decision["decision_index"])
        elif operation == "bounded_search_evaluation":
            if "records" in tokens and "decisions" in tokens:
                record_index = int(tokens[1])
                decision_position = tokens.index("decisions")
                decision = summary["records"][record_index]["decisions"][
                    int(tokens[decision_position + 1])
                ]
                decision_index = int(decision["decision_index"])
                if "actual_card" in tokens or "search_actual_card_comparison" in tokens:
                    origin = "retrospective_attachment"
                    derivation = "retrospective"
                    availability = "after_actual_play"
                    visibility = "public"
                elif "immediate_baseline" in tokens:
                    origin = "heuristic_analysis"
                    derivation = "heuristic"
                    availability = "current_decision"
                    visibility = "public"
                else:
                    origin = "search_derived"
                    derivation = "heuristic"
                    availability = "current_decision"
                    visibility = "public"
        elif operation == "historical_opponent_statistics_aggregation":
            if len(tokens) >= 4 and tokens[0] == "records":
                record_index = int(tokens[1])
                record_prefix = f"/records/{record_index}"
                percentage_dependencies = {
                    "solo_games_played_percent": (
                        f"{record_prefix}/exact_counts/solo_games_played",
                        f"{record_prefix}/games_played",
                    ),
                    "solo_games_won_percent": (
                        f"{record_prefix}/exact_counts/solo_games_won",
                        f"{record_prefix}/exact_counts/solo_games_played",
                    ),
                    "solo_hand_percent": (
                        f"{record_prefix}/exact_counts/solo_hand_games",
                        f"{record_prefix}/exact_counts/solo_games_played",
                    ),
                    "suit_games_percent": (
                        f"{record_prefix}/exact_counts/suit_games",
                        f"{record_prefix}/exact_counts/solo_games_played",
                    ),
                    "grand_games_percent": (
                        f"{record_prefix}/exact_counts/grand_games",
                        f"{record_prefix}/exact_counts/solo_games_played",
                    ),
                    "null_games_percent": (
                        f"{record_prefix}/exact_counts/null_games",
                        f"{record_prefix}/exact_counts/solo_games_played",
                    ),
                    "defender_games_played_percent": (
                        f"{record_prefix}/exact_counts/defender_games_played",
                        f"{record_prefix}/games_played",
                    ),
                    "defender_games_won_percent": (
                        f"{record_prefix}/exact_counts/defender_games_won",
                        f"{record_prefix}/exact_counts/defender_games_played",
                    ),
                }
                if tokens[2] == "statistics":
                    dependencies = percentage_dependencies[tokens[3]]
                elif tokens[2] == "normalized_profile_statistics":
                    profile_dependencies = {
                        "games_played": (f"{record_prefix}/games_played",),
                        "solo_games_played": (f"{record_prefix}/exact_counts/solo_games_played",),
                        "defender_games_played": (
                            f"{record_prefix}/exact_counts/defender_games_played",
                        ),
                        "solo_rate": percentage_dependencies["solo_games_played_percent"],
                        "defender_rate": percentage_dependencies["defender_games_played_percent"],
                        "solo_win_rate": percentage_dependencies["solo_games_won_percent"],
                        "hand_game_rate": percentage_dependencies["solo_hand_percent"],
                        "suit_game_rate": percentage_dependencies["suit_games_percent"],
                        "grand_rate": percentage_dependencies["grand_games_percent"],
                        "null_game_rate": percentage_dependencies["null_games_percent"],
                        "defender_win_rate": percentage_dependencies["defender_games_won_percent"],
                    }
                    dependencies = profile_dependencies[tokens[3]]
                    origin = "rule_derived"
                    derivation = "deterministic_rule"
                elif tokens[2] == "profile_derivation":
                    dependencies = tuple(
                        f"{record_prefix}/normalized_profile_statistics/{field_name}"
                        for field_name in (
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
                        )
                    )
                    origin = "heuristic_analysis"
                    derivation = "heuristic"
        return _entry(
            path,
            origin=origin,
            visibility=visibility,
            available_from=availability,
            derivation=derivation,
            decision_index=decision_index,
            perspective_player_id=perspective_player_id,
            source_references=references,
            dependency_paths=dependencies,
        )

    return build


def _operation_attachment(
    operation: str,
    summary: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    name_by_operation = {
        "summary": "summary",
        "partition_audit": "partition_audit",
        "rolling_opponent_policy_evaluation": "rolling_evaluation",
        "bounded_search_evaluation": "bounded_search_evaluation",
        "historical_opponent_statistics_aggregation": "opponent_statistics_aggregation",
    }
    return build_complete_provenance_attachment(
        name=f"training_dataset/{name_by_operation[operation]}",
        document_role="result",
        document=summary,
        information_use_context=_context("offline_review"),
        entry_builder=_operation_entry_builder(operation, summary),
        validate_entry_use=False,
    )


def _root_attachment(
    operation: str,
    result: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    result_key = next(key for key in result if key != "input_file")

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens == ("input_file",):
            return _entry(
                path,
                origin="caller_supplied",
                visibility="public",
                available_from="request_start",
                derivation="direct",
                decision_index=None,
                perspective_player_id=None,
                source_references=(_reference("request", "application_input_reference"),),
            )
        return _entry(
            path,
            origin="historical_aggregation",
            visibility="post_game_only",
            available_from="offline_review",
            derivation="exact_aggregate",
            decision_index=None,
            perspective_player_id=None,
            source_references=(
                _reference("aggregate", f"training_dataset/{operation}/{result_key}"),
            ),
        )

    return build_complete_provenance_attachment(
        name="training_dataset_result",
        document_role="result",
        document=result,
        information_use_context=_context("offline_review"),
        entry_builder=build,
    )


class TrainingDatasetProvenanceCollector:
    """Collects retained Dataset values without replaying any operation."""

    def __init__(self, options: TrainingDatasetApplicationOptions) -> None:
        self._options = options
        self._dataset: TrainingDatasetInput | None = None

    def capture_dataset(self, dataset: TrainingDatasetInput) -> None:
        self._dataset = dataset

    def build_bundle(
        self,
        result: Mapping[str, object],
        artifacts: tuple[ApplicationArtifact, ...],
    ) -> ApplicationProvenanceBundle:
        if self._dataset is None:
            raise ValueError("Training Dataset provenance did not capture its input.")
        dataset_document = build_serializable_training_dataset_input(self._dataset)
        attachments: list[ApplicationProvenanceAttachment] = [
            _build_dataset_input_attachment(self._dataset),
            *(
                _build_record_attachment(dataset_document, index)
                for index in range(len(self._dataset.records))
            ),
        ]
        operation = self._options.operation
        result_key = next(key for key in result if key != "input_file")
        summary = result[result_key]
        if not isinstance(summary, Mapping):
            raise ValueError("Training Dataset operation result must be an object.")
        if operation == "summary" and "records" in summary:
            records = summary["records"]
            assert isinstance(records, list)
            for record_index, record in enumerate(records):
                assert isinstance(record, Mapping)
                samples = record["samples"]
                assert isinstance(samples, list)
                for sample in samples:
                    assert isinstance(sample, Mapping)
                    metadata = sample["metadata"]
                    features = sample["features"]
                    target = sample["label"]
                    assert isinstance(metadata, Mapping)
                    assert isinstance(features, Mapping)
                    assert isinstance(target, Mapping)
                    common = {
                        "record_index": record_index,
                        "decision_index": int(metadata["decision_index"]),
                        "game_id": str(metadata["source_game_id"]),
                        "player_id": str(metadata["acting_player_id"]),
                        "side": str(metadata["acting_side"]),
                    }
                    attachments.append(_build_feature_attachment(document=features, **common))
                    attachments.append(_build_target_attachment(document=target, **common))
        elif operation == "rolling_opponent_policy_evaluation":
            attachments.extend(_rolling_attachments(summary))
        elif operation == "bounded_search_evaluation":
            attachments.extend(_search_attachments(summary))
        attachments.append(_operation_attachment(operation, summary))
        for artifact in artifacts:
            if artifact.name != "opponent_statistics_input":
                continue
            attachments.append(
                build_complete_provenance_attachment(
                    name="training_dataset/opponent_statistics_input",
                    document_role="result",
                    document=artifact.to_dict(),
                    information_use_context=_context("offline_review"),
                    entry_builder=_offline_entry_builder(
                        _reference("aggregate", "historical_opponent_statistics")
                    ),
                )
            )
        attachments.append(_root_attachment(operation, result))
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.TRAINING_DATASET,
            attachments=tuple(attachments),
        )
