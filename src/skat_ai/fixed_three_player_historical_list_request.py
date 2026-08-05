from dataclasses import dataclass
from typing import Any

from skat_ai.fixed_three_player_historical_list import (
    FixedThreePlayerHistoricalList,
    build_fixed_three_player_historical_list,
)
from skat_ai.performance_rating import validate_stable_list_entry_identifier

FIXED_THREE_PLAYER_HISTORICAL_LIST_REQUEST_SCHEMA_VERSION = 1
MIN_FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON_SOURCE_COUNT = 2


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListAnalysisRequest:
    """One immutable public request for a complete historical-list aggregation."""

    schema_version: int
    historical_list: FixedThreePlayerHistoricalList
    lot_order: tuple[str, ...] | None


@dataclass(frozen=True)
class FixedThreePlayerHistoricalListComparisonRequest:
    """One immutable ordered public request for independent-list comparison."""

    schema_version: int
    lists: tuple[FixedThreePlayerHistoricalListAnalysisRequest, ...]


def _require_exact_fields(
    data: dict[str, Any],
    required_fields: set[str],
    field_name: str,
) -> None:
    missing_fields = sorted(required_fields - data.keys())
    if missing_fields:
        raise ValueError(f"{field_name} is missing required fields: {missing_fields}.")
    unsupported_fields = sorted(data.keys() - required_fields)
    if unsupported_fields:
        raise ValueError(f"{field_name} has unsupported fields: {unsupported_fields}.")


def _validate_request_schema_version(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != 1:
        raise ValueError(f"{field_name} must currently equal 1.")
    return value


def _build_immutable_lot_order(value: Any, field_name: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) not in {2, 3}:
        raise ValueError(f"{field_name} must be null or contain two or three player IDs.")
    for index, player_id in enumerate(value):
        validate_stable_list_entry_identifier(player_id, f"{field_name}[{index}]")
    if len(set(value)) != len(value):
        raise ValueError(f"{field_name} must not contain duplicate player IDs.")
    return tuple(value)


def build_fixed_three_player_historical_list_analysis_request(
    data: dict[str, Any],
    *,
    field_name: str = "fixed_three_player_historical_list_input",
) -> FixedThreePlayerHistoricalListAnalysisRequest:
    """Builds one immutable public list-analysis request with a copied lot order."""
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be an object.")
    _require_exact_fields(
        data,
        {"schema_version", "historical_list", "lot_order"},
        field_name,
    )
    historical_list_data = data["historical_list"]
    if not isinstance(historical_list_data, dict):
        raise ValueError(f"{field_name}.historical_list must be an object.")
    return FixedThreePlayerHistoricalListAnalysisRequest(
        schema_version=_validate_request_schema_version(
            data["schema_version"],
            f"{field_name}.schema_version",
        ),
        historical_list=build_fixed_three_player_historical_list(historical_list_data),
        lot_order=_build_immutable_lot_order(data["lot_order"], f"{field_name}.lot_order"),
    )


def build_fixed_three_player_historical_list_comparison_request(
    data: dict[str, Any],
) -> FixedThreePlayerHistoricalListComparisonRequest:
    """Builds one immutable comparison request while preserving copied source order."""
    field_name = "fixed_three_player_historical_list_comparison_input"
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be an object.")
    _require_exact_fields(data, {"schema_version", "lists"}, field_name)
    raw_lists = data["lists"]
    if not isinstance(raw_lists, list) or len(raw_lists) < 2:
        raise ValueError(f"{field_name}.lists must contain at least two sources.")
    return FixedThreePlayerHistoricalListComparisonRequest(
        schema_version=_validate_request_schema_version(
            data["schema_version"],
            f"{field_name}.schema_version",
        ),
        lists=tuple(
            build_fixed_three_player_historical_list_analysis_request(
                source,
                field_name=f"{field_name}.lists[{index}]",
            )
            for index, source in enumerate(raw_lists)
        ),
    )
