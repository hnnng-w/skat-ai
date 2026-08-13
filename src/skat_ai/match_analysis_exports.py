from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skat_ai.fixed_three_player_historical_list import (
    build_serializable_fixed_three_player_historical_list,
)
from skat_ai.fixed_three_player_historical_list_aggregation import (
    build_serializable_fixed_three_player_historical_list_aggregation,
)
from skat_ai.historical_game import build_serializable_historical_record
from skat_ai.match_analysis_contracts import (
    MATCH_ANALYSIS_REPORT_VERSION,
    MATCH_ARTIFACT_EXPORT_KINDS,
    MATCH_ARTIFACT_EXPORT_VERSION,
    MatchAnalysisReportV1,
    MatchDecisionAnalysisResultV1,
    MatchHistoricalAnalysisResultV1,
    MatchMaterializationReportV1,
)
from skat_ai.match_workspace_materialization import MatchWorkspaceMaterializationV1
from skat_ai.recommendation_workflow import VALID_RECOMMENDATION_METHODS

_SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._~-]+\.json$")
_SAFE_MATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]+$")
_MAX_MATCH_ID_FILENAME_STEM_LENGTH = 96


def _freeze_json(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("document numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("document object keys must be strings.")
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError("document must contain only JSON-compatible values.")


def _thaw_json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchArtifactExportV1:
    """One private deterministic download document without a filesystem path."""

    match_artifact_export_version: int = MATCH_ARTIFACT_EXPORT_VERSION
    export_kind: str
    match_id: str
    workspace_revision: int
    filename: str
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        if (
            type(self.match_artifact_export_version) is not int
            or self.match_artifact_export_version != MATCH_ARTIFACT_EXPORT_VERSION
        ):
            raise ValueError(
                "match_artifact_export_version must equal "
                f"{MATCH_ARTIFACT_EXPORT_VERSION}."
            )
        if self.export_kind not in MATCH_ARTIFACT_EXPORT_KINDS:
            raise ValueError(
                f"export_kind must be one of {list(MATCH_ARTIFACT_EXPORT_KINDS)}."
            )
        if (
            not isinstance(self.match_id, str)
            or not self.match_id
            or self.match_id != self.match_id.strip()
        ):
            raise ValueError("match_id must be a non-empty, non-padded string.")
        if type(self.workspace_revision) is not int or self.workspace_revision < 0:
            raise ValueError("workspace_revision must be a non-negative integer.")
        if (
            not isinstance(self.filename, str)
            or not self.filename.endswith(".json")
            or _SAFE_FILENAME_PATTERN.fullmatch(self.filename) is None
        ):
            raise ValueError("filename must be one ASCII-safe local JSON filename.")
        if not isinstance(self.document, Mapping):
            raise ValueError("document must be an object.")
        object.__setattr__(self, "document", _freeze_json(self.document))

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_artifact_export_version": self.match_artifact_export_version,
            "export_kind": self.export_kind,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "filename": self.filename,
            "document": _thaw_json(self.document),
        }

    def document_to_dict(self) -> dict[str, Any]:
        return _thaw_json(self.document)

    def to_bytes(self) -> bytes:
        return canonical_match_artifact_json_bytes_v1(self.document_to_dict())


def canonical_match_artifact_json_bytes_v1(document: Mapping[str, object]) -> bytes:
    """Serializes one private export with two spaces, LF, and one trailing LF."""
    return (
        json.dumps(
            document,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _build_export(
    *,
    export_kind: str,
    match_id: str,
    workspace_revision: int,
    filename: str,
    document: dict[str, Any],
) -> MatchArtifactExportV1:
    return MatchArtifactExportV1(
        export_kind=export_kind,
        match_id=match_id,
        workspace_revision=workspace_revision,
        filename=filename,
        document=document,
    )


def _filename_match_id(match_id: str) -> str:
    if not isinstance(match_id, str) or not match_id or match_id != match_id.strip():
        raise ValueError("match_id must be a non-empty, non-padded string.")
    if (
        len(match_id) <= _MAX_MATCH_ID_FILENAME_STEM_LENGTH
        and _SAFE_MATCH_ID_PATTERN.fullmatch(match_id) is not None
    ):
        return match_id
    canonical_id = json.dumps(
        match_id,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("ascii")
    return f"match-{hashlib.sha256(canonical_id).hexdigest()}"


def build_match_report_result_export_v1(
    report: MatchAnalysisReportV1,
) -> MatchArtifactExportV1:
    """Exports the exact Root Result from one executed analysis report."""
    if type(report) is not MatchAnalysisReportV1:
        raise ValueError("report must be MatchAnalysisReportV1.")
    if report.match_analysis_report_version != MATCH_ANALYSIS_REPORT_VERSION:
        raise ValueError("report version is unsupported.")
    value = report.value
    filename_match_id = _filename_match_id(report.match_id)
    if type(value) is MatchDecisionAnalysisResultV1:
        if value.result is None:
            raise ValueError("Unavailable Decision analysis has no Root Result export.")
        filename = (
            f"{filename_match_id}-position-{value.match_position:02d}-decision-"
            f"{value.decision_index:02d}-{value.options.recommendation_method}.json"
        )
        if value.options.recommendation_method not in VALID_RECOMMENDATION_METHODS:
            raise ValueError("Decision report has an unsupported recommendation method.")
        document = value.result.to_dict()["document"]
    elif type(value) is MatchHistoricalAnalysisResultV1:
        if value.result is None:
            raise ValueError("Unavailable Historical analysis has no Root Result export.")
        filename = (
            f"{filename_match_id}-game-{value.match_position:02d}-historical-analysis.json"
        )
        document = value.result.to_dict()["document"]
    else:
        raise ValueError("Materialization reports do not contain a Root Result.")
    return _build_export(
        export_kind="report_result",
        match_id=report.match_id,
        workspace_revision=report.workspace_revision,
        filename=filename,
        document=document,
    )


def build_match_materialization_summary_export_v1(
    source: MatchMaterializationReportV1 | MatchWorkspaceMaterializationV1,
) -> MatchArtifactExportV1:
    """Exports the exact internal Workspace materialization representation."""
    materialization = (
        source.materialization
        if type(source) is MatchMaterializationReportV1
        else source
    )
    if type(materialization) is not MatchWorkspaceMaterializationV1:
        raise ValueError("source must contain MatchWorkspaceMaterializationV1.")
    filename_match_id = _filename_match_id(materialization.match_id)
    return _build_export(
        export_kind="materialization_summary",
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        filename=f"{filename_match_id}-materialization.json",
        document=materialization.to_dict(),
    )


def build_match_historical_game_collection_export_v1(
    materialization: MatchWorkspaceMaterializationV1,
) -> MatchArtifactExportV1:
    """Collects available Historical Root inputs in Match-position order."""
    if type(materialization) is not MatchWorkspaceMaterializationV1:
        raise ValueError("materialization must be MatchWorkspaceMaterializationV1.")
    filename_match_id = _filename_match_id(materialization.match_id)
    games = []
    unavailable_positions = []
    for slot in materialization.slot_materializations:
        historical_game = slot.historical_materialization.historical_game
        if historical_game is None:
            unavailable_positions.append(slot.match_position)
            continue
        games.append(
            {
                "match_position": slot.match_position,
                "historical_game_input": build_serializable_historical_record(
                    historical_game
                ),
            }
        )
    document = {
        "match_artifact_export_version": MATCH_ARTIFACT_EXPORT_VERSION,
        "match_id": materialization.match_id,
        "workspace_revision": materialization.workspace_revision,
        "available_game_count": len(games),
        "unavailable_positions": unavailable_positions,
        "games": games,
    }
    return _build_export(
        export_kind="historical_game_collection",
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        filename=f"{filename_match_id}-historical-games.json",
        document=document,
    )


def build_match_training_source_collection_export_v1(
    materialization: MatchWorkspaceMaterializationV1,
) -> MatchArtifactExportV1:
    """Exports the exact existing Match Training source collection."""
    if type(materialization) is not MatchWorkspaceMaterializationV1:
        raise ValueError("materialization must be MatchWorkspaceMaterializationV1.")
    filename_match_id = _filename_match_id(materialization.match_id)
    return _build_export(
        export_kind="training_source_collection",
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        filename=f"{filename_match_id}-training-sources.json",
        document=materialization.training_source_collection.to_dict(),
    )


def build_match_historical_list_input_export_v1(
    materialization: MatchWorkspaceMaterializationV1,
) -> MatchArtifactExportV1:
    """Exports the existing fixed-three-player list Root input when available."""
    if type(materialization) is not MatchWorkspaceMaterializationV1:
        raise ValueError("materialization must be MatchWorkspaceMaterializationV1.")
    historical_list = materialization.historical_list_materialization.historical_list
    if historical_list is None:
        raise ValueError("Historical list input is unavailable.")
    filename_match_id = _filename_match_id(materialization.match_id)
    return _build_export(
        export_kind="historical_list_input",
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        filename=f"{filename_match_id}-historical-list-input.json",
        document={
            "fixed_three_player_historical_list_input": (
                build_serializable_fixed_three_player_historical_list(
                    historical_list
                )
            )
        },
    )


def build_match_historical_list_aggregation_export_v1(
    materialization: MatchWorkspaceMaterializationV1,
) -> MatchArtifactExportV1:
    """Exports the existing serialized fixed-list aggregation when available."""
    if type(materialization) is not MatchWorkspaceMaterializationV1:
        raise ValueError("materialization must be MatchWorkspaceMaterializationV1.")
    aggregation = materialization.historical_list_materialization.aggregation
    if aggregation is None:
        raise ValueError("Historical list aggregation is unavailable.")
    filename_match_id = _filename_match_id(materialization.match_id)
    return _build_export(
        export_kind="historical_list_aggregation",
        match_id=materialization.match_id,
        workspace_revision=materialization.workspace_revision,
        filename=f"{filename_match_id}-historical-list-aggregation.json",
        document=build_serializable_fixed_three_player_historical_list_aggregation(
            aggregation
        ),
    )
