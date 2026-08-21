import json
from collections import Counter
from pathlib import Path

import pytest

import skat_ai.application.position_workflow as position_module
import skat_ai.recommendation_workflow as recommendation_module
from skat_ai.api.v1 import ExecutionOptionsV1, execute_document
from skat_ai.application import (
    ApplicationExecutionOptions,
    HistoricalGameApplicationOptions,
    TrainingDatasetApplicationOptions,
    build_application_invocation,
    execute_application_invocation,
)
from skat_ai.application.execution import ApplicationWorkflowDependencies
from skat_ai.application.historical_game_workflow import (
    HistoricalGameWorkflowDependencies,
)
from skat_ai.application.training_dataset_workflow import (
    TrainingDatasetWorkflowDependencies,
)
from skat_ai.historical_information_set_search_review import (
    build_historical_information_set_search_review_summary_v1,
)
from skat_ai.information_set_search_comparison import (
    build_information_set_search_comparison_pre_actual_analysis_v1,
)
from skat_ai.information_set_search_evaluation import (
    evaluate_information_set_search_dataset_v1,
)
from skat_ai.public_field_provenance import (
    attach_public_field_provenance,
    build_public_field_provenance_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
INFORMATION_SET_SETTINGS = {
    "random_seed": 113,
    "max_remaining_tricks": 1,
    "max_depth_plies": 3,
    "max_state_nodes": 10_000,
    "max_information_sets": 10_000,
    "max_selected_worlds": 1,
    "max_sampled_worlds": 1,
    "minimum_comparable_worlds": 1,
    "wall_clock_timeout_ms": None,
}


def _load(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _position(*, post_game: bool) -> dict[str, object]:
    name = (
        "grand_bounded_search_post_game_review.json"
        if post_game
        else "grand_bounded_search_exhaustive.json"
    )
    document = _load(name)
    document["recommendation_method"] = "information_set_search"
    document["information_set_search_settings"] = dict(INFORMATION_SET_SETTINGS)
    document.pop("bounded_search_settings")
    return document


def _zero_decision_historical() -> dict[str, object]:
    source = _load("historical_grand_declarer_concession.json")
    historical_game = source["historical_game_input"]
    historical_game["game_id"] = "zero-decision-information-set-provenance"
    historical_game["tricks"] = []
    historical_game["game_end"]["declarer_hand_cards_remaining"] = 10
    historical_game["game_end"]["defender_consent"] = {
        "status": "not_required",
        "consenting_defender_player_ids": [],
    }
    return source


def _zero_decision_dataset() -> dict[str, object]:
    source = _load("training_dataset_variable_length.json")
    record = source["training_dataset_input"]["records"][0]
    record["partition"] = "test"
    record["historical_game"] = _zero_decision_historical()[
        "historical_game_input"
    ]
    source["training_dataset_input"]["records"] = [record]
    return source


def _execute_position(document: dict[str, object]):
    return execute_application_invocation(
        build_application_invocation(
            document,
            input_reference="memory://information-set-provenance",
        )
    )


def _attachment(execution, name: str):
    assert execution.provenance is not None
    return next(
        attachment
        for attachment in execution.provenance.attachments
        if attachment.name == name
    )


def _entry(attachment, path: str):
    return next(
        entry for entry in attachment.ledger.entries if entry.field_path == path
    )


def _assert_complete_bundle(execution) -> None:
    assert execution.provenance is not None
    for attachment in execution.provenance.attachments:
        coverage = attachment.coverage_summary
        assert attachment.ledger.status == "complete"
        assert coverage.all_paths_accounted_for is True
        assert coverage.provenance_complete is True
        assert coverage.uncovered_paths == ()
        assert coverage.orphaned_entry_paths == ()
        assert coverage.orphaned_exemption_paths == ()
        assert coverage.overlapping_paths == ()


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def _unavailable_pre_actual(decision_input):
    return build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=None,
        pimc_result=None,
        immediate_recommended_card=decision_input.visible_state.legal_cards[0],
        same_selected_world_sequence=False,
    )


def test_flat_post_game_internal_and_public_provenance_retains_exact_stages() -> None:
    execution = _execute_position(_position(post_game=True))
    _assert_complete_bundle(execution)
    root = _attachment(execution, "position_result")
    input_attachment = _attachment(execution, "flat_retrospective/input")
    analysis = _attachment(execution, "flat_retrospective/analysis")
    assessment = _attachment(execution, "flat_retrospective/assessment")

    assert input_attachment.document["selection"]["settings"][
        "information_set_search_settings"
    ] == INFORMATION_SET_SETTINGS
    settings = _entry(
        root,
        "/settings/information_set_search_settings/random_seed",
    )
    assert settings.origin == "validated_copy"
    assert settings.source_references[0].field_path == (
        "/information_set_search_settings/random_seed"
    )
    requested_depth = _entry(
        root,
        "/information_set_search_result/requested_budget/max_depth_plies",
    )
    assert requested_depth.source_references[0].field_path == (
        "/information_set_search_settings/max_depth_plies"
    )

    status = _entry(root, "/information_set_search_result/status")
    fixed_policy = _entry(
        root,
        "/information_set_search_result/fixed_policy_settings/0/lead_policy",
    )
    actual = _entry(root, "/information_set_search_comparison/actual_card")
    pimc = _entry(root, "/information_set_search_comparison/pimc_status")
    immediate = _entry(
        root,
        "/information_set_search_comparison/immediate_recommended_card",
    )
    strategy_scope = _entry(
        root,
        "/information_set_search_comparison/strategy_fusion_mitigation_scope",
    )
    assert status.source_references[0].reference_id == (
        "bounded_information_set_policy_search_v1"
    )
    assert fixed_policy.source_references[0].reference_id == (
        "effective_opponent_policy"
    )
    assert (actual.origin, actual.available_from) == (
        "retrospective_attachment",
        "after_actual_play",
    )
    assert any("same_selection" in item.reference_id for item in pimc.source_references)
    assert any(
        item.reference_id == "immediate_expected_value"
        for item in immediate.source_references
    )
    assert strategy_scope.source_references[0].reference_type == "rule_contract"

    assert analysis.document["same_selection_pimc_result"] is not None
    assert analysis.document["immediate_baseline"] is not None
    assert assessment.document["information_set_search_comparison"][
        "actual_card"
    ] == execution.result.document["information_set_search_comparison"][
        "actual_card"
    ]
    private_names = {
        "controlled_policy",
        "information_set",
        "observation",
        "observations",
        "world_states",
        "root_information_set",
        "own_remaining_hand",
        "memoization",
        "bundle_cache",
    }
    assert private_names.isdisjoint(
        _all_keys(execution.result.to_dict()["document"])
    )
    assert private_names.isdisjoint(
        set().union(
            *(_all_keys(item.document_to_dict()) for item in execution.provenance.attachments)
        )
    )

    public = build_public_field_provenance_bundle(execution)
    assert public.result.coverage_summary["provenance_complete"] is True
    assert public.result.coverage_summary["overlapping_paths"] == ()
    public_keys = _all_keys(public.to_dict())
    assert "selected_worlds" not in public_keys
    assert "root_information_set" not in public_keys


def test_flat_provenance_and_public_serialization_do_not_rerun_any_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counts = Counter()
    original_recommendation = position_module.execute_recommendation_workflow
    original_information_set = (
        recommendation_module.execute_live_information_set_search_workflow_v1
    )
    original_pimc = position_module.solve_compatible_world_minimax_on_selection_v1

    def recommendation(**kwargs):
        counts[f"recommendation:{kwargs['configuration'].requested_method}"] += 1
        return original_recommendation(**kwargs)

    def information_set(**kwargs):
        counts["information_set"] += 1
        return original_information_set(**kwargs)

    def pimc(**kwargs):
        counts["pimc"] += 1
        return original_pimc(**kwargs)

    monkeypatch.setattr(
        position_module,
        "execute_recommendation_workflow",
        recommendation,
    )
    monkeypatch.setattr(
        recommendation_module,
        "execute_live_information_set_search_workflow_v1",
        information_set,
    )
    monkeypatch.setattr(
        position_module,
        "solve_compatible_world_minimax_on_selection_v1",
        pimc,
    )

    execution = _execute_position(_position(post_game=True))
    expected = Counter(
        {
            "recommendation:information_set_search": 1,
            "recommendation:immediate_expected_value": 1,
            "information_set": 1,
            "pimc": 1,
        }
    )
    assert counts == expected
    build_public_field_provenance_bundle(execution).to_dict()
    attach_public_field_provenance(execution)
    assert counts == expected


def test_public_opt_in_provenance_is_additive_and_omission_is_unchanged() -> None:
    cases = (
        (_position(post_game=False), {}),
        (
            _zero_decision_historical(),
            {
                "information_set_search_review": True,
                "search_seed": 29,
                "immediate_sample_count": 1,
            },
        ),
        (
            _zero_decision_dataset(),
            {
                "operation": "information_set_search_evaluation",
                "information_set_search_seed": 31,
                "information_set_search_partitions": ["test"],
                "information_set_search_max_decisions": 1,
            },
        ),
    )
    for source, workflow_options in cases:
        default = execute_document(
            source,
            options=ExecutionOptionsV1(
                validate_output=False,
                workflow_options=workflow_options,
            ),
        )
        opted_in = execute_document(
            source,
            options=ExecutionOptionsV1(
                validate_output=False,
                include_provenance=True,
                workflow_options=workflow_options,
            ),
        )

        assert default.field_provenance is None
        assert "field_provenance" not in default.result.document
        assert opted_in.field_provenance is not None
        stripped = opted_in.result.to_dict()["document"]
        stripped.pop("field_provenance")
        assert stripped == default.result.to_dict()["document"]
        assert opted_in.field_provenance.result.coverage_summary[
            "provenance_complete"
        ] is True
        assert {
            "controlled_policy",
            "information_set",
            "observation",
            "world_states",
            "root_information_set",
            "own_remaining_hand",
        }.isdisjoint(_all_keys(opted_in.field_provenance.to_dict()))


def test_historical_review_provenance_uses_retained_summary_without_rerun() -> None:
    counts = Counter()

    def build_review(**kwargs):
        counts["review"] += 1

        def pre_actual(decision_input):
            counts["decision"] += 1
            return _unavailable_pre_actual(decision_input)

        return build_historical_information_set_search_review_summary_v1(
            kwargs["snapshot_summary"],
            kwargs["historical_record"],
            kwargs["settings"],
            pre_actual_analysis_builder=pre_actual,
            effective_policy_settings_by_decision=kwargs[
                "effective_policy_settings_by_decision"
            ],
        )

    invocation = build_application_invocation(
        _load("historical_grand_declarer_concession.json"),
        input_reference="memory://historical-information-set-provenance",
        options=ApplicationExecutionOptions(
            historical_game=HistoricalGameApplicationOptions(
                information_set_search_review=True,
                search_seed=17,
                immediate_sample_count=1,
            )
        ),
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=ApplicationWorkflowDependencies(
            historical_game=HistoricalGameWorkflowDependencies(
                build_information_set_search_review=build_review,
            )
        ),
    )
    summary = execution.result.document["historical_game_summary"][
        "historical_information_set_search_review_summary"
    ]
    assert counts == Counter(
        {"review": 1, "decision": summary["decision_count"]}
    )
    _assert_complete_bundle(execution)
    aggregate = _attachment(
        execution,
        "historical_information_set_search_review_summary",
    )
    root = _attachment(execution, "historical_game_result")
    first_analysis = _attachment(execution, "historical_decision/1/analysis")
    first_assessment = _attachment(execution, "historical_decision/1/assessment")

    seed = _entry(aggregate, "/settings/base_search_seed")
    information = _entry(
        first_analysis,
        "/historical_information_set_search_review/information_set_search_result",
    )
    pimc = _entry(
        first_analysis,
        "/historical_information_set_search_review/same_selection_pimc_result",
    )
    immediate = _entry(
        first_analysis,
        "/historical_information_set_search_review/immediate_baseline/recommended_card",
    )
    actual = _entry(
        first_assessment,
        "/historical_information_set_search_review/actual_card",
    )
    assert seed.source_references[0].field_path == "/search_seed"
    assert "information_set" in information.source_references[0].reference_id
    assert "same_selection" in pimc.source_references[0].reference_id
    assert immediate.source_references[0].reference_id == "immediate_expected_value"
    assert actual.available_from == "after_actual_play"
    assert _entry(
        root,
        (
            "/historical_game_summary/"
            "historical_information_set_search_review_summary/"
            "decisions/0/actual_card"
        ),
    ).origin == "retrospective_attachment"

    public = build_public_field_provenance_bundle(execution)
    assert public.result.coverage_summary["provenance_complete"] is True
    assert counts == Counter(
        {"review": 1, "decision": summary["decision_count"]}
    )


def test_dataset_evaluation_provenance_uses_source_options_and_retained_rows() -> None:
    counts = Counter()

    def evaluate(dataset, **kwargs):
        counts["evaluation"] += 1

        def pre_actual(decision_input):
            counts["decision"] += 1
            return _unavailable_pre_actual(decision_input)

        return evaluate_information_set_search_dataset_v1(
            dataset,
            kwargs["base_search_seed"],
            partitions=kwargs["partitions"],
            search_budget_profile=kwargs["search_budget_profile"],
            max_decisions=kwargs["max_decisions"],
            immediate_sample_count=1,
            pre_actual_analysis_builder=pre_actual,
        )

    invocation = build_application_invocation(
        _load("training_dataset_normal_play.json"),
        input_reference="memory://dataset-information-set-provenance",
        options=ApplicationExecutionOptions(
            training_dataset=TrainingDatasetApplicationOptions(
                operation="information_set_search_evaluation",
                information_set_search_seed=23,
                information_set_search_partitions=("validation",),
                information_set_search_max_decisions=1,
            )
        ),
    )
    execution = execute_application_invocation(
        invocation,
        dependencies=ApplicationWorkflowDependencies(
            training_dataset=TrainingDatasetWorkflowDependencies(
                evaluate_information_set_search=evaluate,
            )
        ),
    )
    assert counts == Counter({"evaluation": 1, "decision": 1})
    _assert_complete_bundle(execution)
    aggregate = _attachment(
        execution,
        "training_dataset/information_set_search_evaluation",
    )
    root = _attachment(execution, "training_dataset_result")
    stage_names = {
        attachment.name.rsplit("/", 1)[-1]
        for attachment in execution.provenance.attachments
        if attachment.name.startswith("training_dataset/information_set_search/")
    }
    assert stage_names == {
        "input",
        "information_set",
        "pimc",
        "immediate",
        "actual",
        "comparison",
    }
    seed = _entry(aggregate, "/settings/base_search_seed")
    immediate_default = _entry(aggregate, "/settings/immediate_sample_count")
    partitions = _entry(aggregate, "/selection/partitions/0")
    actual = next(
        entry
        for entry in root.ledger.entries
        if entry.field_path.endswith("/decisions/0/actual_card")
    )
    assert seed.source_references[0].field_path == (
        "/information_set_search_seed"
    )
    assert immediate_default.origin == "defaulted"
    assert immediate_default.source_references[0].field_path == (
        "/immediate_sample_count"
    )
    assert partitions.source_references[0].field_path == (
        "/information_set_search_partitions"
    )
    assert (actual.origin, actual.available_from) == (
        "retrospective_attachment",
        "after_actual_play",
    )
    public = build_public_field_provenance_bundle(execution)
    assert public.result.coverage_summary["provenance_complete"] is True
    assert counts == Counter({"evaluation": 1, "decision": 1})
