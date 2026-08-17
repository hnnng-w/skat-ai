from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.match_player_snapshot import MatchPlayerStatisticsSnapshotV1
from skat_ai.match_player_statistics_context import (
    classify_match_player_statistics_temporal_status_v1,
)
from skat_ai.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    OpponentStatisticsInput,
    OpponentStatisticsRecord,
    build_opponent_statistics_input,
    build_serializable_opponent_statistics_input,
)
from skat_ai.rfc3339 import parse_rfc3339_datetime

if TYPE_CHECKING:
    from skat_ai.learning_corpus_player_catalog import LearningCorpusPlayerCatalogV1

LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION = 1
LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION = 1

LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES: Final[tuple[str, ...]] = (
    "latest_unambiguous",
    "explicit_observation",
)
LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_STATUSES: Final[tuple[str, ...]] = (
    "available",
    "unavailable",
)
LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "player_not_found",
    "target_time_unavailable",
    "no_statistics_history",
    "no_prior_snapshot",
    "explicit_observation_not_found",
    "explicit_observation_not_before_target",
    "ambiguous_latest_instant",
)

LEARNING_CORPUS_PLAYER_STATISTICS_HISTORY_POLICY = "retain_match_bound_observations_without_merge"
LEARNING_CORPUS_PLAYER_STATISTICS_TEMPORAL_POLICY = "captured_strictly_before_target"
LEARNING_CORPUS_PLAYER_STATISTICS_LATEST_POLICY = (
    "latest_unambiguous_content_at_latest_eligible_instant"
)
LEARNING_CORPUS_PLAYER_STATISTICS_EXPLICIT_POLICY = (
    "explicit_observation_requires_temporal_eligibility"
)
LEARNING_CORPUS_PLAYER_STATISTICS_COMBINATION_POLICY = "no_merge_no_weighting_no_averaging"

_STATISTICS_RECORD_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_player_statistics_record_v1\0"
_STATISTICS_OBSERVATION_ID_DOMAIN = b"skat-ai\0learning_corpus_player_statistics_observation_v1\0"


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _require_identifier(
    value: object,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        nullable = " or null" if allow_none else ""
        raise ValueError(f"{field_name} must be a non-empty, non-padded string{nullable}.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_boolean(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _serialize_statistics_record_v1(
    statistics_record: OpponentStatisticsRecord,
) -> dict[str, Any]:
    document = build_serializable_opponent_statistics_input(
        OpponentStatisticsInput(
            schema_version=OPPONENT_STATISTICS_SCHEMA_VERSION,
            records=(statistics_record,),
        )
    )
    return document["opponent_statistics_input"]["records"][0]


def _prepare_statistics_record_v1(
    statistics_record: OpponentStatisticsRecord,
) -> tuple[OpponentStatisticsRecord, dict[str, Any], str]:
    if type(statistics_record) is not OpponentStatisticsRecord:
        raise ValueError("statistics_record must be an exact OpponentStatisticsRecord.")
    serialized = _serialize_statistics_record_v1(statistics_record)
    copied = build_opponent_statistics_input(
        {
            "schema_version": OPPONENT_STATISTICS_SCHEMA_VERSION,
            "records": [serialized],
        }
    ).records[0]
    canonical = _serialize_statistics_record_v1(copied)
    fingerprint = _build_identifier(
        _STATISTICS_RECORD_FINGERPRINT_DOMAIN,
        canonical,
    )
    return copied, canonical, fingerprint


def build_learning_corpus_player_statistics_record_fingerprint_v1(
    statistics_record: OpponentStatisticsRecord,
) -> str:
    """Fingerprints one complete exact validated Opponent Statistics record."""
    return _prepare_statistics_record_v1(statistics_record)[2]


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerStatisticsObservationV1:
    """One exact Match-bound Statistics observation in the current Corpus view."""

    learning_corpus_player_statistics_observation_version: int = (
        LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION
    )
    statistics_observation_id: str
    statistics_record_fingerprint: str
    player_id: str
    match_id: str
    match_snapshot_id: str
    player_match_observation_id: str
    player_observation_id: str
    statistics_snapshot_id: str
    observed_at: str
    captured_at: str
    source_match_played_at: str | None
    source_match_temporal_status: str
    eligible_for_source_match_analysis: bool
    statistics_record: OpponentStatisticsRecord

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlayerStatisticsObservationV1 must be constructed by its "
            "focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        statistics_observation_id: str,
        statistics_record_fingerprint: str,
        player_id: str,
        match_id: str,
        match_snapshot_id: str,
        player_match_observation_id: str,
        player_observation_id: str,
        statistics_snapshot_id: str,
        observed_at: str,
        captured_at: str,
        source_match_played_at: str | None,
        source_match_temporal_status: str,
        eligible_for_source_match_analysis: bool,
        statistics_record: OpponentStatisticsRecord,
    ) -> LearningCorpusPlayerStatisticsObservationV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_player_statistics_observation_version",
                LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION,
            ),
            ("statistics_observation_id", statistics_observation_id),
            ("statistics_record_fingerprint", statistics_record_fingerprint),
            ("player_id", player_id),
            ("match_id", match_id),
            ("match_snapshot_id", match_snapshot_id),
            ("player_match_observation_id", player_match_observation_id),
            ("player_observation_id", player_observation_id),
            ("statistics_snapshot_id", statistics_snapshot_id),
            ("observed_at", observed_at),
            ("captured_at", captured_at),
            ("source_match_played_at", source_match_played_at),
            ("source_match_temporal_status", source_match_temporal_status),
            (
                "eligible_for_source_match_analysis",
                eligible_for_source_match_analysis,
            ),
            ("statistics_record", statistics_record),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_player_statistics_observation_version,
            LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION,
            "learning_corpus_player_statistics_observation_version",
        )
        for field_name in (
            "statistics_observation_id",
            "statistics_record_fingerprint",
            "match_snapshot_id",
            "player_match_observation_id",
            "player_observation_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in (
            "player_id",
            "match_id",
            "statistics_snapshot_id",
            "observed_at",
            "captured_at",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        _require_identifier(
            self.source_match_played_at,
            "source_match_played_at",
            allow_none=True,
        )
        observed_instant = parse_rfc3339_datetime(self.observed_at, "observed_at")
        captured_instant = parse_rfc3339_datetime(self.captured_at, "captured_at")
        if observed_instant != captured_instant:
            raise ValueError("observed_at and captured_at must represent the same instant.")
        if self.source_match_played_at is not None:
            parse_rfc3339_datetime(
                self.source_match_played_at,
                "source_match_played_at",
            )
        if self.source_match_temporal_status not in (
            "eligible",
            "match_time_unavailable",
            "captured_not_before_match",
        ):
            raise ValueError("source_match_temporal_status must be canonical.")
        _require_boolean(
            self.eligible_for_source_match_analysis,
            "eligible_for_source_match_analysis",
        )
        if self.eligible_for_source_match_analysis != (
            self.source_match_temporal_status == "eligible"
        ):
            raise ValueError(
                "eligible_for_source_match_analysis must be true exactly for eligible."
            )
        if type(self.statistics_record) is not OpponentStatisticsRecord:
            raise ValueError("statistics_record must be an exact OpponentStatisticsRecord.")
        if self.statistics_record.player_id != self.player_id:
            raise ValueError("Statistics record Player identity must reconcile.")
        if self.statistics_record.source.captured_at != self.captured_at:
            raise ValueError("captured_at must retain the exact Statistics source value.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_player_statistics_observation_version": (
                self.learning_corpus_player_statistics_observation_version
            ),
            "statistics_observation_id": self.statistics_observation_id,
            "statistics_record_fingerprint": self.statistics_record_fingerprint,
            "player_id": self.player_id,
            "match_id": self.match_id,
            "match_snapshot_id": self.match_snapshot_id,
            "player_match_observation_id": self.player_match_observation_id,
            "player_observation_id": self.player_observation_id,
            "statistics_snapshot_id": self.statistics_snapshot_id,
            "observed_at": self.observed_at,
            "captured_at": self.captured_at,
            "source_match_played_at": self.source_match_played_at,
            "source_match_temporal_status": self.source_match_temporal_status,
            "eligible_for_source_match_analysis": (self.eligible_for_source_match_analysis),
            "statistics_record": _serialize_statistics_record_v1(self.statistics_record),
        }


def _build_learning_corpus_player_statistics_observation_v1(
    *,
    player_id: str,
    match_id: str,
    match_snapshot_id: str,
    player_match_observation_id: str,
    player_observation_id: str,
    statistics_snapshot: MatchPlayerStatisticsSnapshotV1,
    source_match_played_at: str | None,
) -> LearningCorpusPlayerStatisticsObservationV1:
    if type(statistics_snapshot) is not MatchPlayerStatisticsSnapshotV1:
        raise ValueError("statistics_snapshot must be an exact MatchPlayerStatisticsSnapshotV1.")
    copied_record, _, record_fingerprint = _prepare_statistics_record_v1(
        statistics_snapshot.statistics_record
    )
    if copied_record.player_id != player_id:
        raise ValueError("Statistics Snapshot Player identity must reconcile.")
    observed_at = statistics_snapshot.observed_at
    captured_at = copied_record.source.captured_at
    if parse_rfc3339_datetime(observed_at, "observed_at") != parse_rfc3339_datetime(
        captured_at,
        "captured_at",
    ):
        raise ValueError("observed_at and captured_at must represent the same instant.")
    temporal_status = classify_match_player_statistics_temporal_status_v1(
        captured_at=captured_at,
        played_at=source_match_played_at,
    )
    identity_material = {
        "learning_corpus_player_statistics_observation_version": (
            LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION
        ),
        "match_snapshot_id": match_snapshot_id,
        "player_id": player_id,
        "statistics_snapshot_id": statistics_snapshot.snapshot_id,
        "observed_at": observed_at,
        "statistics_record_fingerprint": record_fingerprint,
    }
    return LearningCorpusPlayerStatisticsObservationV1._from_validated(
        statistics_observation_id=_build_identifier(
            _STATISTICS_OBSERVATION_ID_DOMAIN,
            identity_material,
        ),
        statistics_record_fingerprint=record_fingerprint,
        player_id=player_id,
        match_id=match_id,
        match_snapshot_id=match_snapshot_id,
        player_match_observation_id=player_match_observation_id,
        player_observation_id=player_observation_id,
        statistics_snapshot_id=statistics_snapshot.snapshot_id,
        observed_at=observed_at,
        captured_at=captured_at,
        source_match_played_at=source_match_played_at,
        source_match_temporal_status=temporal_status,
        eligible_for_source_match_analysis=temporal_status == "eligible",
        statistics_record=copied_record,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerStatisticsSelectionV1:
    """One normal time-safe Statistics-history selection result."""

    learning_corpus_player_statistics_selection_version: int = (
        LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION
    )
    status: str
    selection_mode: str
    unavailable_reason: str | None
    player_id: str
    target_played_at: str | None
    requested_statistics_observation_id: str | None
    candidate_observation_ids: tuple[str, ...]
    selected_observation: LearningCorpusPlayerStatisticsObservationV1 | None
    equivalent_observation_ids: tuple[str, ...]
    ambiguous_observation_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlayerStatisticsSelectionV1 must be constructed by its focused selector."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        status: str,
        selection_mode: str,
        unavailable_reason: str | None,
        player_id: str,
        target_played_at: str | None,
        requested_statistics_observation_id: str | None,
        candidate_observation_ids: tuple[str, ...],
        selected_observation: LearningCorpusPlayerStatisticsObservationV1 | None,
        equivalent_observation_ids: tuple[str, ...],
        ambiguous_observation_ids: tuple[str, ...],
    ) -> LearningCorpusPlayerStatisticsSelectionV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_player_statistics_selection_version",
                LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION,
            ),
            ("status", status),
            ("selection_mode", selection_mode),
            ("unavailable_reason", unavailable_reason),
            ("player_id", player_id),
            ("target_played_at", target_played_at),
            (
                "requested_statistics_observation_id",
                requested_statistics_observation_id,
            ),
            ("candidate_observation_ids", candidate_observation_ids),
            ("selected_observation", selected_observation),
            ("equivalent_observation_ids", equivalent_observation_ids),
            ("ambiguous_observation_ids", ambiguous_observation_ids),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_player_statistics_selection_version,
            LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION,
            "learning_corpus_player_statistics_selection_version",
        )
        if self.status not in LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_STATUSES:
            raise ValueError("status must be one canonical Statistics selection status.")
        if self.selection_mode not in LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES:
            raise ValueError("selection_mode must be one canonical Statistics selection mode.")
        _require_identifier(self.player_id, "player_id")
        _require_identifier(
            self.target_played_at,
            "target_played_at",
            allow_none=True,
        )
        if self.target_played_at is not None and self.unavailable_reason != "player_not_found":
            parse_rfc3339_datetime(self.target_played_at, "target_played_at")
        if self.requested_statistics_observation_id is not None:
            _require_hash(
                self.requested_statistics_observation_id,
                "requested_statistics_observation_id",
            )
        if self.selection_mode == "latest_unambiguous":
            if self.requested_statistics_observation_id is not None:
                raise ValueError("latest_unambiguous does not accept an observation ID.")
        elif self.requested_statistics_observation_id is None:
            raise ValueError("explicit_observation requires one observation ID.")
        for field_name in (
            "candidate_observation_ids",
            "equivalent_observation_ids",
            "ambiguous_observation_ids",
        ):
            values = getattr(self, field_name)
            if type(values) is not tuple or len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be one unique immutable tuple.")
            for observation_id in values:
                _require_hash(observation_id, field_name)
        if self.status == "available":
            if self.unavailable_reason is not None:
                raise ValueError("An available selection has no unavailable reason.")
            if type(self.selected_observation) is not (LearningCorpusPlayerStatisticsObservationV1):
                raise ValueError("An available selection requires one exact observation.")
            if self.selected_observation.player_id != self.player_id:
                raise ValueError("Selected observation Player identity must reconcile.")
            if self.ambiguous_observation_ids:
                raise ValueError("An available selection cannot be ambiguous.")
        else:
            if self.unavailable_reason not in (
                LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS
            ):
                raise ValueError("An unavailable selection requires one canonical reason.")
            if self.selected_observation is not None:
                raise ValueError("An unavailable selection cannot select an observation.")
            if self.equivalent_observation_ids:
                raise ValueError("An unavailable selection cannot report equivalents.")
        if self.target_played_at is None and self.unavailable_reason not in (
            "player_not_found",
            "target_time_unavailable",
        ):
            raise ValueError(
                "A null target is retained only before Player or target-time availability."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_player_statistics_selection_version": (
                self.learning_corpus_player_statistics_selection_version
            ),
            "status": self.status,
            "selection_mode": self.selection_mode,
            "unavailable_reason": self.unavailable_reason,
            "player_id": self.player_id,
            "target_played_at": self.target_played_at,
            "requested_statistics_observation_id": (self.requested_statistics_observation_id),
            "candidate_observation_ids": list(self.candidate_observation_ids),
            "selected_observation": (
                None if self.selected_observation is None else self.selected_observation.to_dict()
            ),
            "equivalent_observation_ids": list(self.equivalent_observation_ids),
            "ambiguous_observation_ids": list(self.ambiguous_observation_ids),
        }


def _build_selection(
    *,
    status: str,
    selection_mode: str,
    unavailable_reason: str | None,
    player_id: str,
    target_played_at: str | None,
    requested_statistics_observation_id: str | None,
    candidate_observation_ids: tuple[str, ...] = (),
    selected_observation: LearningCorpusPlayerStatisticsObservationV1 | None = None,
    equivalent_observation_ids: tuple[str, ...] = (),
    ambiguous_observation_ids: tuple[str, ...] = (),
) -> LearningCorpusPlayerStatisticsSelectionV1:
    return LearningCorpusPlayerStatisticsSelectionV1._from_validated(
        status=status,
        selection_mode=selection_mode,
        unavailable_reason=unavailable_reason,
        player_id=player_id,
        target_played_at=target_played_at,
        requested_statistics_observation_id=requested_statistics_observation_id,
        candidate_observation_ids=candidate_observation_ids,
        selected_observation=selected_observation,
        equivalent_observation_ids=equivalent_observation_ids,
        ambiguous_observation_ids=ambiguous_observation_ids,
    )


def select_learning_corpus_player_statistics_as_of_v1(
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    player_id: str,
    target_played_at: str | None,
    selection_mode: str,
    statistics_observation_id: str | None = None,
) -> LearningCorpusPlayerStatisticsSelectionV1:
    """Selects one exact retained observation under a strict target-time boundary."""
    from skat_ai.learning_corpus_player_catalog import (
        LearningCorpusPlayerCatalogV1,
        _validate_learning_corpus_player_catalog_v1,
    )

    if type(player_catalog) is not LearningCorpusPlayerCatalogV1:
        raise ValueError("player_catalog must be an exact LearningCorpusPlayerCatalogV1.")
    _validate_learning_corpus_player_catalog_v1(player_catalog)
    return _select_learning_corpus_player_statistics_as_of_validated_v1(
        player_catalog,
        player_id=player_id,
        target_played_at=target_played_at,
        selection_mode=selection_mode,
        statistics_observation_id=statistics_observation_id,
    )


def _select_learning_corpus_player_statistics_as_of_validated_v1(
    player_catalog: LearningCorpusPlayerCatalogV1,
    *,
    player_id: str,
    target_played_at: str | None,
    selection_mode: str,
    statistics_observation_id: str | None = None,
) -> LearningCorpusPlayerStatisticsSelectionV1:
    """Selects from one already validated exact Player Catalog."""
    _require_identifier(player_id, "player_id")
    if selection_mode not in LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES:
        raise ValueError("selection_mode must be one canonical Statistics selection mode.")
    if statistics_observation_id is not None:
        _require_hash(statistics_observation_id, "statistics_observation_id")
    if selection_mode == "latest_unambiguous":
        if statistics_observation_id is not None:
            raise ValueError("latest_unambiguous does not accept an observation ID.")
    elif statistics_observation_id is None:
        raise ValueError("explicit_observation requires one observation ID.")

    player = next(
        (entry for entry in player_catalog.players if entry.player_id == player_id),
        None,
    )
    common = {
        "selection_mode": selection_mode,
        "player_id": player_id,
        "target_played_at": target_played_at,
        "requested_statistics_observation_id": statistics_observation_id,
    }
    if player is None:
        return _build_selection(
            status="unavailable",
            unavailable_reason="player_not_found",
            **common,
        )
    if target_played_at is None:
        return _build_selection(
            status="unavailable",
            unavailable_reason="target_time_unavailable",
            **common,
        )
    _require_identifier(target_played_at, "target_played_at")
    target_instant = parse_rfc3339_datetime(target_played_at, "target_played_at")
    if not player.statistics_observations:
        return _build_selection(
            status="unavailable",
            unavailable_reason="no_statistics_history",
            **common,
        )

    eligible_values: list[LearningCorpusPlayerStatisticsObservationV1] = []
    requested = None
    requested_is_eligible = False
    for observation in player.statistics_observations:
        is_eligible = (
            parse_rfc3339_datetime(observation.captured_at, "captured_at") < target_instant
        )
        if is_eligible:
            eligible_values.append(observation)
        if (
            selection_mode == "explicit_observation"
            and observation.statistics_observation_id == statistics_observation_id
        ):
            requested = observation
            requested_is_eligible = is_eligible
    eligible = tuple(eligible_values)
    candidate_ids = tuple(observation.statistics_observation_id for observation in eligible)
    if selection_mode == "explicit_observation":
        if requested is None:
            return _build_selection(
                status="unavailable",
                unavailable_reason="explicit_observation_not_found",
                candidate_observation_ids=candidate_ids,
                **common,
            )
        if not requested_is_eligible:
            return _build_selection(
                status="unavailable",
                unavailable_reason="explicit_observation_not_before_target",
                candidate_observation_ids=candidate_ids,
                **common,
            )
        return _build_selection(
            status="available",
            unavailable_reason=None,
            candidate_observation_ids=candidate_ids,
            selected_observation=requested,
            **common,
        )

    if not eligible:
        return _build_selection(
            status="unavailable",
            unavailable_reason="no_prior_snapshot",
            candidate_observation_ids=(),
            **common,
        )
    latest_instant = parse_rfc3339_datetime(eligible[-1].captured_at, "captured_at")
    latest = tuple(
        observation
        for observation in eligible
        if parse_rfc3339_datetime(observation.captured_at, "captured_at") == latest_instant
    )
    fingerprints = {observation.statistics_record_fingerprint for observation in latest}
    latest_ids = tuple(sorted(observation.statistics_observation_id for observation in latest))
    if len(fingerprints) != 1:
        return _build_selection(
            status="unavailable",
            unavailable_reason="ambiguous_latest_instant",
            candidate_observation_ids=candidate_ids,
            ambiguous_observation_ids=latest_ids,
            **common,
        )
    selected_id = latest_ids[0]
    selected = next(
        observation
        for observation in latest
        if observation.statistics_observation_id == selected_id
    )
    return _build_selection(
        status="available",
        unavailable_reason=None,
        candidate_observation_ids=candidate_ids,
        selected_observation=selected,
        equivalent_observation_ids=latest_ids,
        **common,
    )
