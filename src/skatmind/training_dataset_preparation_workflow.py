from dataclasses import dataclass
from typing import Any

from skatmind.dataset_partition_audit import (
    DatasetPartitionAudit,
    build_serializable_dataset_partition_audit,
)
from skatmind.dataset_partition_plan import (
    COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
    DATASET_PARTITION_BALANCE_BASIS,
    DATASET_PARTITION_PLAN_VERSION,
    TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    CompleteDatasetPartitionPlan,
    DatasetPartitionPlan,
    UnavailableDatasetPartitionPlan,
    build_dataset_partition_plan_fingerprint,
    build_serializable_dataset_partition_plan,
)
from skatmind.dataset_partition_policy import DATASET_PARTITION_POLICY_VERSION
from skatmind.dataset_preparation_identity import (
    build_source_content_fingerprint,
    build_source_identity_fingerprint,
)
from skatmind.player_disjoint_unseen_player_split import (
    generate_component_balanced_unseen_player_dataset_partition_plan,
)
from skatmind.temporal_known_opponent_split import (
    generate_temporal_known_opponent_dataset_partition_plan,
)
from skatmind.training_dataset import (
    TrainingDatasetInput,
    build_serializable_training_dataset_input,
)
from skatmind.training_dataset_preparation import (
    TRAINING_DATASET_PREPARATION_VERSION,
    TrainingDatasetPreparationRequest,
    materialize_prepared_training_dataset,
)

_ALGORITHM_BY_MODE = {
    "known_opponent": TEMPORAL_KNOWN_OPPONENT_ALGORITHM,
    "unseen_player": COMPONENT_BALANCED_UNSEEN_PLAYER_ALGORITHM,
}
_UNAVAILABLE_REASONS_BY_MODE = {
    "known_opponent": {
        "missing_played_at",
        "insufficient_time_groups",
        "known_opponent_train_coverage_unsatisfied",
        "non_empty_partition_requirement_unsatisfied",
    },
    "unseen_player": {
        "insufficient_player_components",
        "component_distribution_infeasible",
        "non_empty_partition_requirement_unsatisfied",
    },
}


@dataclass(frozen=True)
class TrainingDatasetPreparationResult:
    """One public complete or unavailable automatic preparation result."""

    preparation_version: int
    plan: DatasetPartitionPlan
    training_dataset_input: TrainingDatasetInput | None
    partition_audit: DatasetPartitionAudit | None


def _validate_request(request: TrainingDatasetPreparationRequest) -> None:
    if not isinstance(request, TrainingDatasetPreparationRequest):
        raise ValueError("request must be a TrainingDatasetPreparationRequest value.")
    if request.preparation_version != TRAINING_DATASET_PREPARATION_VERSION:
        raise ValueError("request preparation version is unsupported.")


def _source_sample_count(request: TrainingDatasetPreparationRequest) -> int:
    # Loading already validates each play prefix; counting supplied plays avoids replay.
    return sum(
        len(trick.plays)
        for record in request.records
        for trick in record.historical_game.tricks
    )


def validate_training_dataset_preparation_result(
    request: TrainingDatasetPreparationRequest,
    result: TrainingDatasetPreparationResult,
) -> None:
    """Reconciles a public result without rerunning a generator or replaying games."""
    _validate_request(request)
    if not isinstance(result, TrainingDatasetPreparationResult):
        raise ValueError("result must be a TrainingDatasetPreparationResult value.")
    if (
        request.preparation_version != TRAINING_DATASET_PREPARATION_VERSION
        or result.preparation_version != request.preparation_version
    ):
        raise ValueError("Preparation result version does not match the request.")

    plan = result.plan
    if not isinstance(plan, DatasetPartitionPlan):
        raise ValueError("Preparation result plan must be a DatasetPartitionPlan value.")
    expected_algorithm = _ALGORITHM_BY_MODE.get(request.mode)
    if expected_algorithm is None:
        raise ValueError(f"Unsupported Training Dataset preparation mode '{request.mode}'.")
    if plan.plan_version != DATASET_PARTITION_PLAN_VERSION:
        raise ValueError("Preparation result Plan version is unsupported.")
    if plan.mode != request.mode or plan.algorithm != expected_algorithm:
        raise ValueError("Preparation result Plan mode or algorithm does not match the request.")
    if plan.base_random_seed != request.base_random_seed:
        raise ValueError("Preparation result Plan seed does not match the request.")
    if plan.balance_basis != DATASET_PARTITION_BALANCE_BASIS:
        raise ValueError("Preparation result Plan balance basis is unsupported.")
    if plan.requested_partition_weights != request.partition_weights:
        raise ValueError("Preparation result Plan weights do not match the request.")
    if plan.source_record_count != len(request.records):
        raise ValueError("Preparation result Plan source Record Count does not match the request.")
    if plan.source_sample_count != _source_sample_count(request):
        raise ValueError("Preparation result Plan source Sample Count does not match the request.")
    if plan.source_identity_fingerprint != build_source_identity_fingerprint(request):
        raise ValueError("Preparation result source identity fingerprint does not match.")
    if plan.source_content_fingerprint != build_source_content_fingerprint(request):
        raise ValueError("Preparation result source content fingerprint does not match.")
    if plan.plan_fingerprint != build_dataset_partition_plan_fingerprint(plan):
        raise ValueError("Preparation result Plan fingerprint does not match its fields.")

    if plan.status == "complete":
        if not isinstance(plan, CompleteDatasetPartitionPlan):
            raise ValueError("A complete result requires CompleteDatasetPartitionPlan.")
        dataset = result.training_dataset_input
        audit = result.partition_audit
        if dataset is None or audit is None:
            raise ValueError("A complete result requires materialized Dataset and audit values.")
        if plan.unavailable_reason is not None:
            raise ValueError("A complete result must not have an unavailable reason.")
        if plan.partition_audit is None:
            raise ValueError("A complete result requires a Plan partition audit.")
        if (request.mode == "known_opponent") != (plan.temporal_audit is not None):
            raise ValueError("Preparation result temporal audit does not match its mode.")
        if (
            dataset.dataset_id != request.dataset_id
            or dataset.dataset_version != request.dataset_version
            or dataset.feature_generation_version != request.feature_generation_version
            or dataset.target != request.target
        ):
            raise ValueError("Materialized Training Dataset identity does not match the request.")
        if (
            dataset.partition_policy is None
            or dataset.partition_policy.policy_version != DATASET_PARTITION_POLICY_VERSION
            or dataset.partition_policy.mode != request.mode
        ):
            raise ValueError("Materialized Training Dataset policy does not match the request.")
        if len(dataset.records) != len(request.records):
            raise ValueError("Materialized Training Dataset Record Count does not match.")
        for source_record, materialized_record in zip(
            request.records,
            dataset.records,
            strict=True,
        ):
            if (
                materialized_record.record_id != source_record.record_id
                or materialized_record.provenance != source_record.provenance
                or materialized_record.historical_game != source_record.historical_game
            ):
                raise ValueError(
                    f"Materialized record '{source_record.record_id}' does not "
                    "losslessly preserve its source Record."
                )
        if build_serializable_dataset_partition_audit(
            audit
        ) != build_serializable_dataset_partition_audit(plan.partition_audit):
            raise ValueError("Preparation result audit does not match the Plan audit.")
        return

    if plan.status != "unavailable" or not isinstance(
        plan, UnavailableDatasetPartitionPlan
    ):
        raise ValueError("Preparation result Plan status is unsupported.")
    if plan.unavailable_reason not in _UNAVAILABLE_REASONS_BY_MODE[request.mode]:
        raise ValueError("Preparation result unavailable reason does not match its mode.")
    if (
        plan.assignments
        or plan.partition_summaries
        or plan.temporal_audit is not None
        or plan.partition_audit is not None
        or result.training_dataset_input is not None
        or result.partition_audit is not None
    ):
        raise ValueError(
            "An unavailable result must not contain materialization or partial Plan data."
        )


def build_training_dataset_preparation_result(
    request: TrainingDatasetPreparationRequest,
) -> TrainingDatasetPreparationResult:
    """Dispatches one mode-specific generator and materializes only complete Plans."""
    _validate_request(request)
    if request.mode == "known_opponent":
        plan = generate_temporal_known_opponent_dataset_partition_plan(request)
    elif request.mode == "unseen_player":
        plan = generate_component_balanced_unseen_player_dataset_partition_plan(request)
    else:
        raise ValueError(f"Unsupported Training Dataset preparation mode '{request.mode}'.")

    if plan.status == "complete":
        prepared = materialize_prepared_training_dataset(request, plan)
        result = TrainingDatasetPreparationResult(
            preparation_version=prepared.preparation_version,
            plan=prepared.plan,
            training_dataset_input=prepared.training_dataset_input,
            partition_audit=prepared.partition_audit,
        )
    else:
        result = TrainingDatasetPreparationResult(
            preparation_version=request.preparation_version,
            plan=plan,
            training_dataset_input=None,
            partition_audit=None,
        )
    validate_training_dataset_preparation_result(request, result)
    return result


def build_serializable_training_dataset_preparation_result(
    request: TrainingDatasetPreparationRequest,
    result: TrainingDatasetPreparationResult,
) -> dict[str, Any]:
    """Serializes exactly the stable public preparation-result contract."""
    validate_training_dataset_preparation_result(request, result)
    return {
        "preparation_version": result.preparation_version,
        "plan": build_serializable_dataset_partition_plan(result.plan),
        "training_dataset_input": (
            build_serializable_training_dataset_input(result.training_dataset_input)
            if result.training_dataset_input is not None
            else None
        ),
        "partition_audit": (
            build_serializable_dataset_partition_audit(result.partition_audit)
            if result.partition_audit is not None
            else None
        ),
    }
