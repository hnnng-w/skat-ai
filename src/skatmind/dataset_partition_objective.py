from skatmind.training_dataset_preparation import DatasetPartitionWeights


def build_record_count_objective(
    *,
    train_count: int,
    validation_count: int,
    test_count: int,
    source_count: int,
    weights: DatasetPartitionWeights,
) -> tuple[int, int, int, int, int]:
    """Builds the shared exact weighted Record-count deviation objective."""
    total_weight = weights.total_weight
    deviations = (
        train_count * total_weight - source_count * weights.train,
        validation_count * total_weight - source_count * weights.validation,
        test_count * total_weight - source_count * weights.test,
    )
    absolute_deviations = tuple(abs(deviation) for deviation in deviations)
    return (
        sum(absolute_deviations),
        max(absolute_deviations),
        absolute_deviations[0],
        absolute_deviations[1],
        absolute_deviations[2],
    )
