from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    build_serializable_historical_decision_snapshot,
)
from skat_ai.learning_corpus_human_evidence import (
    LearningCorpusCommentaryEvidenceV1,
    LearningCorpusResponseEvidenceV1,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_player_statistics import (
    LearningCorpusPlayerStatisticsObservationV1,
    LearningCorpusPlayerStatisticsSelectionV1,
)
from skat_ai.learning_corpus_strategy_teacher import (
    LearningCorpusStrategyTeacherEvidenceV1,
    _strategy_teacher_evidence_sort_key_v1,
)
from skat_ai.match_decision_review_preparation import (
    MATCH_DECISION_REVIEW_SKIP_REASONS,
)
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.rfc3339 import parse_rfc3339_datetime

LEARNING_DATASET_VERSION = 2
LEARNING_DATASET_SOURCE_CONTEXT_VERSION = 1
LEARNING_DATASET_DECISION_STATE_VERSION = 1
LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION = 1
LEARNING_DATASET_PLAYER_CONTEXT_VERSION = 1
LEARNING_DATASET_RECORD_VERSION = 1
LEARNING_DATASET_SKIPPED_DECISION_VERSION = 1

LEARNING_DATASET_STATUSES: Final[tuple[str, ...]] = (
    "empty",
    "unavailable",
    "partial",
    "complete",
)
LEARNING_DATASET_EVIDENCE_FAMILIES: Final[tuple[str, ...]] = (
    "observed_behavior",
    "player_context",
    "strategy_teacher",
    "human_commentary",
    "linked_response",
)
LEARNING_DATASET_RELATIVE_PLAYERS: Final[tuple[str, ...]] = (
    "me",
    "left",
    "right",
)

LEARNING_DATASET_SOURCE_POLICY = "explicit_current_match_snapshots_only"
LEARNING_DATASET_DECISION_STATE_POLICY = "before_actual_play_information_safe_state"
LEARNING_DATASET_OBSERVED_BEHAVIOR_POLICY = (
    "actual_card_is_observed_behavior_not_universal_target"
)
LEARNING_DATASET_EVIDENCE_SEPARATION_POLICY = (
    "behavior_strategy_and_communication_remain_separate"
)
LEARNING_DATASET_HUMAN_TEXT_POLICY = (
    "preserve_exact_human_evidence_without_interpretation"
)
LEARNING_DATASET_STRATEGY_TEACHER_POLICY = (
    "retain_all_method_bound_teacher_evidence_without_preference"
)
LEARNING_DATASET_PLAYER_CONTEXT_POLICY = (
    "latest_unambiguous_strictly_prior_statistics_without_profile_derivation"
)
LEARNING_DATASET_UNAVAILABLE_CONTEXT_POLICY = (
    "preserve_selection_status_reason_and_source_observation_ids"
)
LEARNING_DATASET_PARTITION_POLICY = (
    "unpartitioned_match_snapshot_grouping_reserved_for_later_preparation"
)
LEARNING_DATASET_TASK_POLICY = "task_neutral_no_default_target_or_label"
LEARNING_DATASET_DERIVED_TAG_POLICY = "no_derived_communication_tags_in_version_2"
LEARNING_DATASET_PRIVACY_POLICY = "private_local_unredacted_learning_evidence"
LEARNING_DATASET_EXPORT_POLICY = "deterministic_path_free_json_document"

_SOURCE_CONTEXT_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_source_context_v1\0"
)
_DECISION_STATE_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_decision_state_v1\0"
)
_OBSERVED_BEHAVIOR_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_observed_behavior_v1\0"
)
_RECORD_ID_DOMAIN = b"skat-ai\0learning_dataset_v2_record_v1\0"
_RECORD_CONTENT_FINGERPRINT_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_record_content_v1\0"
)
_SKIPPED_DECISION_ID_DOMAIN = (
    b"skat-ai\0learning_dataset_v2_skipped_decision_v1\0"
)
_DATASET_FINGERPRINT_DOMAIN = b"skat-ai\0learning_dataset_v2_collection_v2\0"


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(
        domain + build_learning_corpus_canonical_json_bytes_v1(value)
    ).hexdigest()


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


def _require_count(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_hash_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        _require_hash(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique IDs.")
    return value


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in {bool, int, float, str}:
        return value
    raise ValueError("Decision State must contain only finite JSON-compatible values.")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


def _copy_timecode(value: MediaTimecodeV1 | None) -> MediaTimecodeV1 | None:
    if value is None:
        return None
    if type(value) is not MediaTimecodeV1:
        raise ValueError("Source Context timecodes must be exact MediaTimecodeV1 values.")
    return MediaTimecodeV1(
        media_timecode_version=value.media_timecode_version,
        start_offset_ms=value.start_offset_ms,
        end_offset_ms=value.end_offset_ms,
    )


def _timecode_dict(value: MediaTimecodeV1 | None) -> dict[str, int | None] | None:
    return None if value is None else value.to_dict()


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetSourceContextV1:
    learning_dataset_source_context_version: int = LEARNING_DATASET_SOURCE_CONTEXT_VERSION
    source_context_fingerprint: str
    match_snapshot_id: str
    game_reference_id: str
    match_id: str
    workspace_revision: int
    match_position: int
    game_id: str
    match_title: str
    external_match_id: str | None
    played_at: str | None
    game_platform: str
    source_kind: str
    source_url: str | None
    source_title: str
    source_channel_name: str | None
    match_timecode: MediaTimecodeV1 | None
    game_timecode: MediaTimecodeV1 | None
    decision_timecode: MediaTimecodeV1 | None
    perspective_player_id: str
    forehand_player_id: str
    middlehand_player_id: str
    rearhand_player_id: str
    declarer_player_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetSourceContextV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetSourceContextV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_source_context_version",
            LEARNING_DATASET_SOURCE_CONTEXT_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in {"match_timecode", "game_timecode", "decision_timecode"}:
                field_value = _copy_timecode(field_value)
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_dataset_source_context_version,
            LEARNING_DATASET_SOURCE_CONTEXT_VERSION,
            "learning_dataset_source_context_version",
        )
        for field_name in ("source_context_fingerprint", "match_snapshot_id", "game_reference_id"):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in (
            "match_id",
            "game_id",
            "match_title",
            "game_platform",
            "source_kind",
            "source_title",
            "perspective_player_id",
            "forehand_player_id",
            "middlehand_player_id",
            "rearhand_player_id",
            "declarer_player_id",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        for field_name in (
            "external_match_id",
            "played_at",
            "source_url",
            "source_channel_name",
        ):
            _require_identifier(getattr(self, field_name), field_name, allow_none=True)
        _require_count(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        seats = (
            self.forehand_player_id,
            self.middlehand_player_id,
            self.rearhand_player_id,
        )
        if len(set(seats)) != 3:
            raise ValueError("Source Context seats must contain three unique Players.")
        if self.perspective_player_id not in seats or self.declarer_player_id not in seats:
            raise ValueError("Perspective Player and Declarer must belong to the Game.")
        if verify_fingerprint and self.source_context_fingerprint != _build_identifier(
            _SOURCE_CONTEXT_FINGERPRINT_DOMAIN,
            _source_context_fingerprint_material(self),
        ):
            raise ValueError("source_context_fingerprint must cover the exact Source Context.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_source_context_version": self.learning_dataset_source_context_version,
            "source_context_fingerprint": self.source_context_fingerprint,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "match_title": self.match_title,
            "external_match_id": self.external_match_id,
            "played_at": self.played_at,
            "game_platform": self.game_platform,
            "source_kind": self.source_kind,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_channel_name": self.source_channel_name,
            "match_timecode": _timecode_dict(self.match_timecode),
            "game_timecode": _timecode_dict(self.game_timecode),
            "decision_timecode": _timecode_dict(self.decision_timecode),
            "perspective_player_id": self.perspective_player_id,
            "forehand_player_id": self.forehand_player_id,
            "middlehand_player_id": self.middlehand_player_id,
            "rearhand_player_id": self.rearhand_player_id,
            "declarer_player_id": self.declarer_player_id,
        }


def _source_context_fingerprint_material(
    value: LearningDatasetSourceContextV1,
) -> dict[str, Any]:
    material = value.to_dict()
    del material["source_context_fingerprint"]
    return material


def _build_source_context_v1(**values: Any) -> LearningDatasetSourceContextV1:
    provisional = LearningDatasetSourceContextV1._from_validated(
        source_context_fingerprint="0" * 64,
        **values,
    )
    return LearningDatasetSourceContextV1._from_validated(
        source_context_fingerprint=_build_identifier(
            _SOURCE_CONTEXT_FINGERPRINT_DOMAIN,
            _source_context_fingerprint_material(provisional),
        ),
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetDecisionStateV1:
    learning_dataset_decision_state_version: int = LEARNING_DATASET_DECISION_STATE_VERSION
    decision_state_fingerprint: str
    decision_reference_id: str
    source_game_id: str
    source_played_at: str | None
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    acting_side: str
    information_cutoff: str
    relative_player_map: Mapping[str, str]
    visible_state: Mapping[str, object]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetDecisionStateV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetDecisionStateV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_decision_state_version",
            LEARNING_DATASET_DECISION_STATE_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in {"relative_player_map", "visible_state"}:
                field_value = _freeze_json(field_value)
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_dataset_decision_state_version,
            LEARNING_DATASET_DECISION_STATE_VERSION,
            "learning_dataset_decision_state_version",
        )
        _require_hash(self.decision_state_fingerprint, "decision_state_fingerprint")
        _require_hash(self.decision_reference_id, "decision_reference_id")
        _require_identifier(self.source_game_id, "source_game_id")
        _require_identifier(self.source_played_at, "source_played_at", allow_none=True)
        for field_name in ("decision_index", "trick_number", "play_index"):
            if type(getattr(self, field_name)) is not int or getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be a positive integer.")
        _require_identifier(self.acting_player_id, "acting_player_id")
        if self.acting_seat not in {"forehand", "middlehand", "rearhand"}:
            raise ValueError("acting_seat must be one canonical historical seat.")
        if self.acting_side not in {"declarer", "defenders"}:
            raise ValueError("acting_side must be declarer or defenders.")
        if self.information_cutoff != "before_actual_play":
            raise ValueError("information_cutoff must equal before_actual_play.")
        if tuple(self.relative_player_map) != LEARNING_DATASET_RELATIVE_PLAYERS:
            raise ValueError("relative_player_map must use canonical relative-player order.")
        if len(set(self.relative_player_map.values())) != 3:
            raise ValueError("relative_player_map must contain three distinct Players.")
        if self.relative_player_map["me"] != self.acting_player_id:
            raise ValueError("relative_player_map me must equal the acting Player.")
        visible = _thaw_json(self.visible_state)
        if not isinstance(visible, dict):
            raise ValueError("visible_state must be one immutable JSON object.")
        if "actual_card_played" in visible:
            raise ValueError("Decision State must exclude the actual Card.")
        if verify_fingerprint and self.decision_state_fingerprint != _build_identifier(
            _DECISION_STATE_FINGERPRINT_DOMAIN,
            _decision_state_fingerprint_material(self),
        ):
            raise ValueError("decision_state_fingerprint must cover the exact Decision State.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_decision_state_version": self.learning_dataset_decision_state_version,
            "decision_state_fingerprint": self.decision_state_fingerprint,
            "decision_reference_id": self.decision_reference_id,
            "source_game_id": self.source_game_id,
            "source_played_at": self.source_played_at,
            "decision_index": self.decision_index,
            "trick_number": self.trick_number,
            "play_index": self.play_index,
            "acting_player_id": self.acting_player_id,
            "acting_seat": self.acting_seat,
            "acting_side": self.acting_side,
            "information_cutoff": self.information_cutoff,
            "relative_player_map": dict(self.relative_player_map),
            "visible_state": _thaw_json(self.visible_state),
        }


def _decision_state_fingerprint_material(
    value: LearningDatasetDecisionStateV1,
) -> dict[str, Any]:
    material = value.to_dict()
    del material["decision_state_fingerprint"]
    return material


def _build_decision_state_v1(
    snapshot: HistoricalDecisionSnapshot,
    *,
    decision_reference_id: str,
) -> LearningDatasetDecisionStateV1:
    if type(snapshot) is not HistoricalDecisionSnapshot:
        raise ValueError("snapshot must be an exact HistoricalDecisionSnapshot.")
    serialized = build_serializable_historical_decision_snapshot(snapshot)
    values = {
        "decision_reference_id": decision_reference_id,
        "source_game_id": snapshot.source_game_id,
        "source_played_at": snapshot.source_played_at,
        "decision_index": snapshot.decision_index,
        "trick_number": snapshot.trick_number,
        "play_index": snapshot.play_index,
        "acting_player_id": snapshot.acting_player_id,
        "acting_seat": snapshot.acting_seat,
        "acting_side": snapshot.acting_side,
        "information_cutoff": snapshot.information_cutoff,
        "relative_player_map": serialized["relative_player_map"],
        "visible_state": serialized["visible_state"],
    }
    provisional = LearningDatasetDecisionStateV1._from_validated(
        decision_state_fingerprint="0" * 64,
        **values,
    )
    return LearningDatasetDecisionStateV1._from_validated(
        decision_state_fingerprint=_build_identifier(
            _DECISION_STATE_FINGERPRINT_DOMAIN,
            _decision_state_fingerprint_material(provisional),
        ),
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetObservedBehaviorV1:
    learning_dataset_observed_behavior_version: int = LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION
    observed_behavior_fingerprint: str
    decision_reference_id: str
    actual_card_played: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetObservedBehaviorV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetObservedBehaviorV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_observed_behavior_version",
            LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_dataset_observed_behavior_version,
            LEARNING_DATASET_OBSERVED_BEHAVIOR_VERSION,
            "learning_dataset_observed_behavior_version",
        )
        _require_hash(self.observed_behavior_fingerprint, "observed_behavior_fingerprint")
        _require_hash(self.decision_reference_id, "decision_reference_id")
        _require_identifier(self.actual_card_played, "actual_card_played")
        if verify_fingerprint and self.observed_behavior_fingerprint != _build_identifier(
            _OBSERVED_BEHAVIOR_FINGERPRINT_DOMAIN,
            _observed_behavior_fingerprint_material(self),
        ):
            raise ValueError("observed_behavior_fingerprint must cover the exact behavior.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_observed_behavior_version": (
                self.learning_dataset_observed_behavior_version
            ),
            "observed_behavior_fingerprint": self.observed_behavior_fingerprint,
            "decision_reference_id": self.decision_reference_id,
            "actual_card_played": self.actual_card_played,
        }


def _observed_behavior_fingerprint_material(
    value: LearningDatasetObservedBehaviorV1,
) -> dict[str, Any]:
    material = value.to_dict()
    del material["observed_behavior_fingerprint"]
    return material


def _build_observed_behavior_v1(
    *,
    decision_reference_id: str,
    actual_card_played: str,
) -> LearningDatasetObservedBehaviorV1:
    values = {
        "decision_reference_id": decision_reference_id,
        "actual_card_played": actual_card_played,
    }
    provisional = LearningDatasetObservedBehaviorV1._from_validated(
        observed_behavior_fingerprint="0" * 64,
        **values,
    )
    return LearningDatasetObservedBehaviorV1._from_validated(
        observed_behavior_fingerprint=_build_identifier(
            _OBSERVED_BEHAVIOR_FINGERPRINT_DOMAIN,
            _observed_behavior_fingerprint_material(provisional),
        ),
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetPlayerContextV1:
    learning_dataset_player_context_version: int = LEARNING_DATASET_PLAYER_CONTEXT_VERSION
    relative_player: str
    player_id: str
    selection_mode: str
    selection_status: str
    unavailable_reason: str | None
    target_played_at: str | None
    candidate_observation_ids: tuple[str, ...]
    selected_statistics_observation_id: str | None
    equivalent_observation_ids: tuple[str, ...]
    ambiguous_observation_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetPlayerContextV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetPlayerContextV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_player_context_version",
            LEARNING_DATASET_PLAYER_CONTEXT_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_dataset_player_context_version,
            LEARNING_DATASET_PLAYER_CONTEXT_VERSION,
            "learning_dataset_player_context_version",
        )
        if self.relative_player not in LEARNING_DATASET_RELATIVE_PLAYERS:
            raise ValueError("relative_player must be me, left, or right.")
        _require_identifier(self.player_id, "player_id")
        if self.selection_mode != "latest_unambiguous":
            raise ValueError("selection_mode must equal latest_unambiguous.")
        if self.selection_status not in {"available", "unavailable"}:
            raise ValueError("selection_status must be available or unavailable.")
        _require_identifier(self.unavailable_reason, "unavailable_reason", allow_none=True)
        _require_identifier(self.target_played_at, "target_played_at", allow_none=True)
        for field_name in (
            "candidate_observation_ids",
            "equivalent_observation_ids",
            "ambiguous_observation_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)
        if self.selected_statistics_observation_id is not None:
            _require_hash(
                self.selected_statistics_observation_id,
                "selected_statistics_observation_id",
            )
        if self.selection_status == "available":
            if (
                self.unavailable_reason is not None
                or self.selected_statistics_observation_id is None
            ):
                raise ValueError("Available Player Context requires one selected observation.")
        elif self.unavailable_reason is None or self.selected_statistics_observation_id is not None:
            raise ValueError("Unavailable Player Context requires one reason and no selection.")
        elif self.unavailable_reason not in {
            "player_not_found",
            "target_time_unavailable",
            "no_statistics_history",
            "no_prior_snapshot",
            "ambiguous_latest_instant",
        }:
            raise ValueError(
                "Unavailable latest-unambiguous Player Context has an invalid reason."
            )
        if self.selection_status == "unavailable" and self.equivalent_observation_ids:
            raise ValueError("Unavailable Player Context cannot retain equivalent IDs.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_player_context_version": self.learning_dataset_player_context_version,
            "relative_player": self.relative_player,
            "player_id": self.player_id,
            "selection_mode": self.selection_mode,
            "selection_status": self.selection_status,
            "unavailable_reason": self.unavailable_reason,
            "target_played_at": self.target_played_at,
            "candidate_observation_ids": list(self.candidate_observation_ids),
            "selected_statistics_observation_id": self.selected_statistics_observation_id,
            "equivalent_observation_ids": list(self.equivalent_observation_ids),
            "ambiguous_observation_ids": list(self.ambiguous_observation_ids),
        }


def _build_player_context_v1(
    relative_player: str,
    selection: LearningCorpusPlayerStatisticsSelectionV1,
) -> LearningDatasetPlayerContextV1:
    if type(selection) is not LearningCorpusPlayerStatisticsSelectionV1:
        raise ValueError("selection must be an exact Statistics selection.")
    selected_id = (
        None
        if selection.selected_observation is None
        else selection.selected_observation.statistics_observation_id
    )
    return LearningDatasetPlayerContextV1._from_validated(
        relative_player=relative_player,
        player_id=selection.player_id,
        selection_mode=selection.selection_mode,
        selection_status=selection.status,
        unavailable_reason=selection.unavailable_reason,
        target_played_at=selection.target_played_at,
        candidate_observation_ids=selection.candidate_observation_ids,
        selected_statistics_observation_id=selected_id,
        equivalent_observation_ids=selection.equivalent_observation_ids,
        ambiguous_observation_ids=selection.ambiguous_observation_ids,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetRecordV1:
    learning_dataset_record_version: int = LEARNING_DATASET_RECORD_VERSION
    record_id: str
    record_content_fingerprint: str
    source_context: LearningDatasetSourceContextV1
    decision_state: LearningDatasetDecisionStateV1
    observed_behavior: LearningDatasetObservedBehaviorV1
    player_contexts: tuple[LearningDatasetPlayerContextV1, ...]
    evidence_families_present: tuple[str, ...]
    strategy_teacher_evidence_ids: tuple[str, ...]
    commentary_evidence_ids: tuple[str, ...]
    outgoing_response_evidence_ids: tuple[str, ...]
    incoming_response_evidence_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetRecordV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetRecordV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_record_version",
            LEARNING_DATASET_RECORD_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identities=False)
        return value

    def _validate(self, *, verify_identities: bool) -> None:
        _require_version(
            self.learning_dataset_record_version,
            LEARNING_DATASET_RECORD_VERSION,
            "learning_dataset_record_version",
        )
        _require_hash(self.record_id, "record_id")
        _require_hash(self.record_content_fingerprint, "record_content_fingerprint")
        self.source_context._validate(verify_fingerprint=verify_identities)
        self.decision_state._validate(verify_fingerprint=verify_identities)
        self.observed_behavior._validate(verify_fingerprint=verify_identities)
        decision_id = self.decision_state.decision_reference_id
        if self.observed_behavior.decision_reference_id != decision_id:
            raise ValueError("Record State and Observed Behavior must use one Decision.")
        if self.source_context.game_id != self.decision_state.source_game_id:
            raise ValueError("Record Source Context and Decision State Game must reconcile.")
        if self.source_context.played_at != self.decision_state.source_played_at:
            raise ValueError("Record Source Context and Decision State time must reconcile.")
        seats_by_name = {
            "forehand": self.source_context.forehand_player_id,
            "middlehand": self.source_context.middlehand_player_id,
            "rearhand": self.source_context.rearhand_player_id,
        }
        if set(self.decision_state.relative_player_map.values()) != set(
            seats_by_name.values()
        ):
            raise ValueError("Decision relative Players must equal Source Context seats.")
        if seats_by_name[self.decision_state.acting_seat] != (
            self.decision_state.acting_player_id
        ):
            raise ValueError("Decision acting seat must match Source Context.")
        expected_side = (
            "declarer"
            if self.decision_state.acting_player_id
            == self.source_context.declarer_player_id
            else "defenders"
        )
        if self.decision_state.acting_side != expected_side:
            raise ValueError("Decision acting side must match the Source Context Declarer.")
        if type(self.player_contexts) is not tuple or len(self.player_contexts) != 3:
            raise ValueError("player_contexts must contain exactly three values.")
        for context in self.player_contexts:
            if type(context) is not LearningDatasetPlayerContextV1:
                raise ValueError("player_contexts must contain exact Player Context values.")
            context._validate()
        if tuple(item.relative_player for item in self.player_contexts) != (
            LEARNING_DATASET_RELATIVE_PLAYERS
        ):
            raise ValueError("Player Contexts must use canonical relative-player order.")
        if tuple(item.player_id for item in self.player_contexts) != tuple(
            self.decision_state.relative_player_map[key]
            for key in LEARNING_DATASET_RELATIVE_PLAYERS
        ):
            raise ValueError("Player Contexts must equal the Decision relative Player map.")
        for field_name in (
            "strategy_teacher_evidence_ids",
            "commentary_evidence_ids",
            "outgoing_response_evidence_ids",
            "incoming_response_evidence_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)
        expected_families = (
            "observed_behavior",
            "player_context",
            *(("strategy_teacher",) if self.strategy_teacher_evidence_ids else ()),
            *(("human_commentary",) if self.commentary_evidence_ids else ()),
            *(
                ("linked_response",)
                if self.outgoing_response_evidence_ids
                or self.incoming_response_evidence_ids
                else ()
            ),
        )
        if self.evidence_families_present != expected_families:
            raise ValueError("evidence_families_present must match exact Record evidence.")
        if verify_identities:
            if self.record_id != _build_identifier(
                _RECORD_ID_DOMAIN,
                _record_identity_material(self),
            ):
                raise ValueError("record_id must cover the stable source Decision identity.")
            if self.record_content_fingerprint != _build_identifier(
                _RECORD_CONTENT_FINGERPRINT_DOMAIN,
                _record_content_fingerprint_material(self),
            ):
                raise ValueError("record_content_fingerprint must cover the enriched Record.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_record_version": self.learning_dataset_record_version,
            "record_id": self.record_id,
            "record_content_fingerprint": self.record_content_fingerprint,
            "source_context": self.source_context.to_dict(),
            "decision_state": self.decision_state.to_dict(),
            "observed_behavior": self.observed_behavior.to_dict(),
            "player_contexts": [item.to_dict() for item in self.player_contexts],
            "evidence_families_present": list(self.evidence_families_present),
            "strategy_teacher_evidence_ids": list(self.strategy_teacher_evidence_ids),
            "commentary_evidence_ids": list(self.commentary_evidence_ids),
            "outgoing_response_evidence_ids": list(self.outgoing_response_evidence_ids),
            "incoming_response_evidence_ids": list(self.incoming_response_evidence_ids),
        }


def _record_identity_material(value: LearningDatasetRecordV1) -> dict[str, Any]:
    return {
        "learning_dataset_record_version": LEARNING_DATASET_RECORD_VERSION,
        "match_snapshot_id": value.source_context.match_snapshot_id,
        "decision_reference_id": value.decision_state.decision_reference_id,
    }


def _record_content_fingerprint_material(value: LearningDatasetRecordV1) -> dict[str, Any]:
    material = value.to_dict()
    del material["record_content_fingerprint"]
    return material


def _build_record_v1(**values: Any) -> LearningDatasetRecordV1:
    provisional = LearningDatasetRecordV1._from_validated(
        record_id="0" * 64,
        record_content_fingerprint="0" * 64,
        **values,
    )
    record_id = _build_identifier(_RECORD_ID_DOMAIN, _record_identity_material(provisional))
    with_id = LearningDatasetRecordV1._from_validated(
        record_id=record_id,
        record_content_fingerprint="0" * 64,
        **values,
    )
    return LearningDatasetRecordV1._from_validated(
        record_id=record_id,
        record_content_fingerprint=_build_identifier(
            _RECORD_CONTENT_FINGERPRINT_DOMAIN,
            _record_content_fingerprint_material(with_id),
        ),
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetSkippedDecisionV1:
    learning_dataset_skipped_decision_version: int = LEARNING_DATASET_SKIPPED_DECISION_VERSION
    skipped_decision_id: str
    match_snapshot_id: str
    game_reference_id: str
    decision_reference_id: str
    match_id: str
    match_position: int
    game_id: str
    decision_index: int
    acting_player_id: str
    reason: str
    commentary_evidence_ids: tuple[str, ...]
    outgoing_response_evidence_ids: tuple[str, ...]
    incoming_response_evidence_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetSkippedDecisionV1 must be constructed by its builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetSkippedDecisionV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_dataset_skipped_decision_version",
            LEARNING_DATASET_SKIPPED_DECISION_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_identity=False)
        return value

    def _validate(self, *, verify_identity: bool) -> None:
        _require_version(
            self.learning_dataset_skipped_decision_version,
            LEARNING_DATASET_SKIPPED_DECISION_VERSION,
            "learning_dataset_skipped_decision_version",
        )
        for field_name in (
            "skipped_decision_id",
            "match_snapshot_id",
            "game_reference_id",
            "decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in ("match_id", "game_id", "acting_player_id"):
            _require_identifier(getattr(self, field_name), field_name)
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        if type(self.decision_index) is not int or self.decision_index <= 0:
            raise ValueError("decision_index must be a positive integer.")
        if self.reason not in MATCH_DECISION_REVIEW_SKIP_REASONS:
            raise ValueError("reason must reuse the Match Decision skip vocabulary.")
        for field_name in (
            "commentary_evidence_ids",
            "outgoing_response_evidence_ids",
            "incoming_response_evidence_ids",
        ):
            _require_hash_tuple(getattr(self, field_name), field_name)
        if verify_identity and self.skipped_decision_id != _build_identifier(
            _SKIPPED_DECISION_ID_DOMAIN,
            _skipped_decision_identity_material(self),
        ):
            raise ValueError("skipped_decision_id must cover the exact skipped Decision.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_skipped_decision_version": (
                self.learning_dataset_skipped_decision_version
            ),
            "skipped_decision_id": self.skipped_decision_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "decision_reference_id": self.decision_reference_id,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "reason": self.reason,
            "commentary_evidence_ids": list(self.commentary_evidence_ids),
            "outgoing_response_evidence_ids": list(self.outgoing_response_evidence_ids),
            "incoming_response_evidence_ids": list(self.incoming_response_evidence_ids),
        }


def _skipped_decision_identity_material(
    value: LearningDatasetSkippedDecisionV1,
) -> dict[str, Any]:
    material = value.to_dict()
    del material["skipped_decision_id"]
    return material


def _build_skipped_decision_v1(**values: Any) -> LearningDatasetSkippedDecisionV1:
    provisional = LearningDatasetSkippedDecisionV1._from_validated(
        skipped_decision_id="0" * 64,
        **values,
    )
    return LearningDatasetSkippedDecisionV1._from_validated(
        skipped_decision_id=_build_identifier(
            _SKIPPED_DECISION_ID_DOMAIN,
            _skipped_decision_identity_material(provisional),
        ),
        **values,
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningDatasetV2:
    learning_dataset_version: int = LEARNING_DATASET_VERSION
    dataset_id: str
    dataset_fingerprint: str
    status: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    player_catalog_fingerprint: str
    human_evidence_collection_fingerprint: str
    strategy_teacher_collection_fingerprint: str
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    observed_game_count: int
    observed_decision_count: int
    record_count: int
    skipped_decision_count: int
    selected_statistics_context_count: int
    statistics_observation_count: int
    strategy_teacher_evidence_count: int
    commentary_evidence_count: int
    response_evidence_count: int
    records_with_strategy_teacher_count: int
    records_with_commentary_count: int
    records_with_outgoing_response_count: int
    records_with_incoming_response_count: int
    unjoined_commentary_evidence_count: int
    unjoined_response_evidence_count: int
    records: tuple[LearningDatasetRecordV1, ...]
    skipped_decisions: tuple[LearningDatasetSkippedDecisionV1, ...]
    player_statistics_observations: tuple[LearningCorpusPlayerStatisticsObservationV1, ...]
    strategy_teacher_evidences: tuple[LearningCorpusStrategyTeacherEvidenceV1, ...]
    commentary_evidences: tuple[LearningCorpusCommentaryEvidenceV1, ...]
    response_evidences: tuple[LearningCorpusResponseEvidenceV1, ...]
    unjoined_commentary_evidence_ids: tuple[str, ...]
    unjoined_response_evidence_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LearningDatasetV2 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningDatasetV2:
        value = object.__new__(cls)
        object.__setattr__(value, "learning_dataset_version", LEARNING_DATASET_VERSION)
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False, validate_nested=False)
        return value

    def _validate(self, *, verify_fingerprint: bool, validate_nested: bool) -> None:
        _require_version(
            self.learning_dataset_version,
            LEARNING_DATASET_VERSION,
            "learning_dataset_version",
        )
        _require_identifier(self.dataset_id, "dataset_id")
        _require_hash(self.dataset_fingerprint, "dataset_fingerprint")
        if self.status not in LEARNING_DATASET_STATUSES:
            raise ValueError("status must be one canonical Learning Dataset status.")
        _require_identifier(self.corpus_id, "corpus_id")
        _require_count(self.source_catalog_revision, "source_catalog_revision")
        for field_name in (
            "source_catalog_fingerprint",
            "source_catalog_content_fingerprint",
            "player_catalog_fingerprint",
            "human_evidence_collection_fingerprint",
            "strategy_teacher_collection_fingerprint",
        ):
            _require_hash(getattr(self, field_name), field_name)
        _require_hash_tuple(self.current_match_snapshot_ids, "current_match_snapshot_ids")
        count_fields = (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "observed_game_count",
            "observed_decision_count",
            "record_count",
            "skipped_decision_count",
            "selected_statistics_context_count",
            "statistics_observation_count",
            "strategy_teacher_evidence_count",
            "commentary_evidence_count",
            "response_evidence_count",
            "records_with_strategy_teacher_count",
            "records_with_commentary_count",
            "records_with_outgoing_response_count",
            "records_with_incoming_response_count",
            "unjoined_commentary_evidence_count",
            "unjoined_response_evidence_count",
        )
        for field_name in count_fields:
            _require_count(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.retained_match_snapshot_count < self.current_match_count:
            raise ValueError("Retained Snapshot count cannot be below Current count.")
        if self.record_count + self.skipped_decision_count != self.observed_decision_count:
            raise ValueError("Records and skipped Decisions must cover every observed Decision.")
        expected_status = (
            "empty"
            if self.observed_decision_count == 0
            else "unavailable"
            if self.record_count == 0
            else "partial"
            if self.skipped_decision_count > 0
            else "complete"
        )
        if self.status != expected_status:
            raise ValueError("status must match safe Decision-state coverage.")
        typed_pools = (
            ("records", LearningDatasetRecordV1),
            ("skipped_decisions", LearningDatasetSkippedDecisionV1),
            ("player_statistics_observations", LearningCorpusPlayerStatisticsObservationV1),
            ("strategy_teacher_evidences", LearningCorpusStrategyTeacherEvidenceV1),
            ("commentary_evidences", LearningCorpusCommentaryEvidenceV1),
            ("response_evidences", LearningCorpusResponseEvidenceV1),
        )
        for field_name, expected_type in typed_pools:
            values = getattr(self, field_name)
            if type(values) is not tuple or any(type(item) is not expected_type for item in values):
                raise ValueError(f"{field_name} must contain exact immutable values.")
        if self.record_count != len(self.records):
            raise ValueError("record_count must reconcile exactly.")
        if self.skipped_decision_count != len(self.skipped_decisions):
            raise ValueError("skipped_decision_count must reconcile exactly.")
        if self.statistics_observation_count != len(self.player_statistics_observations):
            raise ValueError("statistics_observation_count must reconcile exactly.")
        if self.strategy_teacher_evidence_count != len(self.strategy_teacher_evidences):
            raise ValueError("strategy_teacher_evidence_count must reconcile exactly.")
        if self.commentary_evidence_count != len(self.commentary_evidences):
            raise ValueError("commentary_evidence_count must reconcile exactly.")
        if self.response_evidence_count != len(self.response_evidences):
            raise ValueError("response_evidence_count must reconcile exactly.")
        _require_hash_tuple(
            self.unjoined_commentary_evidence_ids,
            "unjoined_commentary_evidence_ids",
        )
        _require_hash_tuple(
            self.unjoined_response_evidence_ids,
            "unjoined_response_evidence_ids",
        )
        if self.unjoined_commentary_evidence_count != len(
            self.unjoined_commentary_evidence_ids
        ):
            raise ValueError("unjoined_commentary_evidence_count must reconcile exactly.")
        if self.unjoined_response_evidence_count != len(self.unjoined_response_evidence_ids):
            raise ValueError("unjoined_response_evidence_count must reconcile exactly.")
        expected_record_order = tuple(
            sorted(
                self.records,
                key=lambda item: (
                    item.source_context.match_id,
                    item.source_context.match_position,
                    item.decision_state.decision_index,
                    item.record_id,
                ),
            )
        )
        expected_skipped_order = tuple(
            sorted(
                self.skipped_decisions,
                key=lambda item: (
                    item.match_id,
                    item.match_position,
                    item.decision_index,
                    item.skipped_decision_id,
                ),
            )
        )
        if self.records != expected_record_order or self.skipped_decisions != (
            expected_skipped_order
        ):
            raise ValueError("Records and skipped Decisions must use canonical source order.")
        record_ids = tuple(item.record_id for item in self.records)
        skipped_ids = tuple(item.skipped_decision_id for item in self.skipped_decisions)
        record_decision_ids = tuple(
            item.decision_state.decision_reference_id for item in self.records
        )
        skipped_decision_ids = tuple(
            item.decision_reference_id for item in self.skipped_decisions
        )
        if len(record_ids) != len(set(record_ids)) or len(skipped_ids) != len(set(skipped_ids)):
            raise ValueError("Record and skipped Decision IDs must be unique.")
        all_decision_ids = (*record_decision_ids, *skipped_decision_ids)
        if len(all_decision_ids) != len(set(all_decision_ids)):
            raise ValueError("Every observed Decision must occur exactly once.")
        if any(
            item.source_context.match_snapshot_id not in self.current_match_snapshot_ids
            for item in self.records
        ) or any(
            item.match_snapshot_id not in self.current_match_snapshot_ids
            for item in self.skipped_decisions
        ):
            raise ValueError("Records and skipped Decisions must use Current Snapshots only.")

        statistics_by_id = {
            item.statistics_observation_id: item
            for item in self.player_statistics_observations
        }
        teachers_by_id = {
            item.strategy_teacher_evidence_id: item
            for item in self.strategy_teacher_evidences
        }
        commentaries_by_id = {
            item.commentary_evidence_id: item for item in self.commentary_evidences
        }
        responses_by_id = {
            item.response_evidence_id: item for item in self.response_evidences
        }
        if any(
            len(values) != expected
            for values, expected in (
                (statistics_by_id, len(self.player_statistics_observations)),
                (teachers_by_id, len(self.strategy_teacher_evidences)),
                (commentaries_by_id, len(self.commentary_evidences)),
                (responses_by_id, len(self.response_evidences)),
            )
        ):
            raise ValueError("Every normalized evidence pool ID must be unique.")
        expected_statistics_order = tuple(
            sorted(
                self.player_statistics_observations,
                key=lambda item: (
                    item.player_id,
                    parse_rfc3339_datetime(item.captured_at, "captured_at"),
                    item.statistics_observation_id,
                ),
            )
        )
        if self.player_statistics_observations != expected_statistics_order:
            raise ValueError("Statistics observations must use canonical Player/time order.")
        if self.strategy_teacher_evidences != tuple(
            sorted(
                self.strategy_teacher_evidences,
                key=_strategy_teacher_evidence_sort_key_v1,
            )
        ):
            raise ValueError("Strategy Teacher Evidence must preserve canonical source order.")

        referenced_statistics: set[str] = set()
        referenced_teachers: list[str] = []
        referenced_commentaries: list[str] = []
        outgoing_responses: list[str] = []
        incoming_responses: list[str] = []
        for record in self.records:
            behavior_card = record.observed_behavior.actual_card_played
            visible_state = record.decision_state.visible_state
            if (
                behavior_card not in visible_state["own_hand"]
                or behavior_card not in visible_state["legal_cards"]
                or behavior_card
                in {item["card"] for item in visible_state["current_trick"]}
            ):
                raise ValueError("Observed Behavior must remain legal in Decision State.")
            for context in record.player_contexts:
                context_ids = (
                    *context.candidate_observation_ids,
                    *context.equivalent_observation_ids,
                    *context.ambiguous_observation_ids,
                    *(
                        (context.selected_statistics_observation_id,)
                        if context.selected_statistics_observation_id is not None
                        else ()
                    ),
                )
                if any(
                    observation_id not in statistics_by_id
                    or statistics_by_id[observation_id].player_id != context.player_id
                    for observation_id in context_ids
                ):
                    raise ValueError(
                        "Player Context Statistics IDs must resolve to the same Player."
                    )
                if context.target_played_at is None:
                    if context_ids:
                        raise ValueError(
                            "A null Player Context target cannot reference Statistics."
                        )
                else:
                    target = parse_rfc3339_datetime(
                        context.target_played_at,
                        "target_played_at",
                    )
                    candidates = tuple(
                        statistics_by_id[item]
                        for item in context.candidate_observation_ids
                    )
                    if any(
                        parse_rfc3339_datetime(item.captured_at, "captured_at") >= target
                        for item in candidates
                    ):
                        raise ValueError(
                            "Player Context candidates must be strictly before the target."
                        )
                    if candidates != tuple(
                        sorted(
                            candidates,
                            key=lambda item: (
                                parse_rfc3339_datetime(item.captured_at, "captured_at"),
                                item.statistics_observation_id,
                            ),
                        )
                    ):
                        raise ValueError(
                            "Player Context candidates must use chronological source order."
                        )
                candidate_ids = set(context.candidate_observation_ids)
                if not set(context.equivalent_observation_ids) <= candidate_ids or not set(
                    context.ambiguous_observation_ids
                ) <= candidate_ids:
                    raise ValueError(
                        "Equivalent and ambiguous Statistics IDs must be candidates."
                    )
                if context.selection_status == "available":
                    selected_id = context.selected_statistics_observation_id
                    assert selected_id is not None
                    if (
                        selected_id not in candidate_ids
                        or selected_id not in context.equivalent_observation_ids
                        or context.ambiguous_observation_ids
                    ):
                        raise ValueError(
                            "Available Player Context selection fields must reconcile."
                        )
                    candidates = tuple(
                        statistics_by_id[item]
                        for item in context.candidate_observation_ids
                    )
                    latest_instant = max(
                        parse_rfc3339_datetime(item.captured_at, "captured_at")
                        for item in candidates
                    )
                    latest = tuple(
                        item
                        for item in candidates
                        if parse_rfc3339_datetime(item.captured_at, "captured_at")
                        == latest_instant
                    )
                    latest_ids = tuple(
                        sorted(item.statistics_observation_id for item in latest)
                    )
                    if (
                        context.equivalent_observation_ids != latest_ids
                        or selected_id != latest_ids[0]
                        or len(
                            {item.statistics_record_fingerprint for item in latest}
                        )
                        != 1
                    ):
                        raise ValueError(
                            "Available Player Context must select latest equivalent content."
                        )
                elif context.unavailable_reason == "ambiguous_latest_instant":
                    if not context.ambiguous_observation_ids:
                        raise ValueError(
                            "Ambiguous Player Context requires ambiguous Observation IDs."
                        )
                    candidates = tuple(
                        statistics_by_id[item]
                        for item in context.candidate_observation_ids
                    )
                    latest_instant = max(
                        parse_rfc3339_datetime(item.captured_at, "captured_at")
                        for item in candidates
                    )
                    latest = tuple(
                        item
                        for item in candidates
                        if parse_rfc3339_datetime(item.captured_at, "captured_at")
                        == latest_instant
                    )
                    if context.ambiguous_observation_ids != tuple(
                        sorted(item.statistics_observation_id for item in latest)
                    ) or len(
                        {item.statistics_record_fingerprint for item in latest}
                    ) <= 1:
                        raise ValueError(
                            "Ambiguous Player Context must retain conflicting latest content."
                        )
                elif context.ambiguous_observation_ids:
                    raise ValueError(
                        "Only ambiguous latest-instant unavailability may retain ambiguity IDs."
                    )
                elif context.candidate_observation_ids and context.unavailable_reason in {
                    "player_not_found",
                    "target_time_unavailable",
                    "no_statistics_history",
                    "no_prior_snapshot",
                }:
                    raise ValueError(
                        "Unavailable Player Context reason conflicts with candidate IDs."
                    )
                referenced_statistics.update(context.candidate_observation_ids)
                referenced_statistics.update(context.equivalent_observation_ids)
                referenced_statistics.update(context.ambiguous_observation_ids)
                if context.selected_statistics_observation_id is not None:
                    referenced_statistics.add(context.selected_statistics_observation_id)
            referenced_teachers.extend(record.strategy_teacher_evidence_ids)
            referenced_commentaries.extend(record.commentary_evidence_ids)
            outgoing_responses.extend(record.outgoing_response_evidence_ids)
            incoming_responses.extend(record.incoming_response_evidence_ids)
        if referenced_statistics != set(statistics_by_id):
            raise ValueError("Statistics pool must contain every referenced value exactly once.")
        if len(referenced_teachers) != len(set(referenced_teachers)) or set(
            referenced_teachers
        ) != set(teachers_by_id):
            raise ValueError("Every Strategy Teacher value must be referenced by one Record.")
        if len(referenced_commentaries) != len(set(referenced_commentaries)) or set(
            referenced_commentaries
        ) != set(commentaries_by_id):
            raise ValueError("Every joined Commentary value must be referenced by one Record.")
        if (
            len(outgoing_responses) != len(set(outgoing_responses))
            or len(incoming_responses) != len(set(incoming_responses))
            or set(outgoing_responses) != set(responses_by_id)
            or set(incoming_responses) != set(responses_by_id)
        ):
            raise ValueError("Every joined Response must have one outgoing and incoming Record.")
        if set(self.unjoined_commentary_evidence_ids).intersection(commentaries_by_id):
            raise ValueError("Joined and unjoined Commentary IDs must be disjoint.")
        if set(self.unjoined_response_evidence_ids).intersection(responses_by_id):
            raise ValueError("Joined and unjoined Response IDs must be disjoint.")
        for skipped in self.skipped_decisions:
            if not set(skipped.commentary_evidence_ids) <= set(
                self.unjoined_commentary_evidence_ids
            ) or not set(
                (*skipped.outgoing_response_evidence_ids, *skipped.incoming_response_evidence_ids)
            ) <= set(self.unjoined_response_evidence_ids):
                raise ValueError("Skipped Decision evidence must be reported as unjoined.")
        skipped_commentaries = [
            evidence_id
            for skipped in self.skipped_decisions
            for evidence_id in skipped.commentary_evidence_ids
        ]
        skipped_outgoing_responses = [
            evidence_id
            for skipped in self.skipped_decisions
            for evidence_id in skipped.outgoing_response_evidence_ids
        ]
        skipped_incoming_responses = [
            evidence_id
            for skipped in self.skipped_decisions
            for evidence_id in skipped.incoming_response_evidence_ids
        ]
        if (
            len(skipped_commentaries) != len(set(skipped_commentaries))
            or set(skipped_commentaries) != set(self.unjoined_commentary_evidence_ids)
        ):
            raise ValueError(
                "Every unjoined Commentary must attach to one skipped Decision."
            )
        if len(skipped_outgoing_responses) != len(
            set(skipped_outgoing_responses)
        ) or len(skipped_incoming_responses) != len(set(skipped_incoming_responses)):
            raise ValueError("Unjoined Response direction IDs must not repeat.")
        if set(self.unjoined_response_evidence_ids) != set(
            (*skipped_outgoing_responses, *skipped_incoming_responses)
        ):
            raise ValueError(
                "Every unjoined Response must attach to a relevant skipped Decision."
            )

        records_by_decision = {
            item.decision_state.decision_reference_id: item for item in self.records
        }
        for teacher in self.strategy_teacher_evidences:
            record = records_by_decision[teacher.decision_reference_id]
            if (
                teacher.strategy_teacher_evidence_id
                not in record.strategy_teacher_evidence_ids
                or
                teacher.match_snapshot_id != record.source_context.match_snapshot_id
                or teacher.game_reference_id != record.source_context.game_reference_id
                or teacher.decision_index != record.decision_state.decision_index
                or teacher.acting_player_id != record.decision_state.acting_player_id
                or teacher.actual_card_played != record.observed_behavior.actual_card_played
            ):
                raise ValueError("Strategy Teacher Evidence must reconcile with its Record.")
        for commentary in self.commentary_evidences:
            record = records_by_decision[commentary.subject_decision_reference_id]
            if (
                commentary.commentary_evidence_id not in record.commentary_evidence_ids
                or
                commentary.match_snapshot_id != record.source_context.match_snapshot_id
                or commentary.game_reference_id != record.source_context.game_reference_id
                or commentary.subject_decision_index != record.decision_state.decision_index
                or commentary.subject_player_id != record.decision_state.acting_player_id
                or commentary.actual_card_played != record.observed_behavior.actual_card_played
            ):
                raise ValueError("Commentary Evidence must reconcile with its Record.")
        for response in self.response_evidences:
            subject = records_by_decision[response.subject_decision_reference_id]
            target = records_by_decision[response.response_decision_reference_id]
            if (
                response.response_evidence_id
                not in subject.outgoing_response_evidence_ids
                or response.response_evidence_id
                not in target.incoming_response_evidence_ids
                or
                response.match_snapshot_id != subject.source_context.match_snapshot_id
                or response.match_snapshot_id != target.source_context.match_snapshot_id
                or response.game_reference_id != subject.source_context.game_reference_id
                or response.game_reference_id != target.source_context.game_reference_id
                or response.response_player_id != target.decision_state.acting_player_id
                or response.response_card_played != target.observed_behavior.actual_card_played
            ):
                raise ValueError("Response Evidence must reconcile with both Records.")

        expected_selected_count = sum(
            context.selected_statistics_observation_id is not None
            for record in self.records
            for context in record.player_contexts
        )
        count_expectations = {
            "selected_statistics_context_count": expected_selected_count,
            "records_with_strategy_teacher_count": sum(
                bool(item.strategy_teacher_evidence_ids) for item in self.records
            ),
            "records_with_commentary_count": sum(
                bool(item.commentary_evidence_ids) for item in self.records
            ),
            "records_with_outgoing_response_count": sum(
                bool(item.outgoing_response_evidence_ids) for item in self.records
            ),
            "records_with_incoming_response_count": sum(
                bool(item.incoming_response_evidence_ids) for item in self.records
            ),
        }
        for field_name, expected in count_expectations.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"{field_name} must reconcile exactly.")
        if validate_nested:
            for record in self.records:
                record._validate(verify_identities=True)
            for skipped in self.skipped_decisions:
                skipped._validate(verify_identity=True)
            for observation in self.player_statistics_observations:
                observation._validate()
            for evidence in self.strategy_teacher_evidences:
                evidence._validate(verify_identities=True)
            for evidence in self.commentary_evidences:
                evidence._validate()
            for evidence in self.response_evidences:
                evidence._validate()
        if verify_fingerprint and self.dataset_fingerprint != _build_identifier(
            _DATASET_FINGERPRINT_DOMAIN,
            _dataset_fingerprint_material(self),
        ):
            raise ValueError("dataset_fingerprint must cover the complete Dataset.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_dataset_version": self.learning_dataset_version,
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "status": self.status,
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": self.source_catalog_content_fingerprint,
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "player_catalog_fingerprint": self.player_catalog_fingerprint,
            "human_evidence_collection_fingerprint": (
                self.human_evidence_collection_fingerprint
            ),
            "strategy_teacher_collection_fingerprint": (
                self.strategy_teacher_collection_fingerprint
            ),
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "observed_game_count": self.observed_game_count,
            "observed_decision_count": self.observed_decision_count,
            "record_count": self.record_count,
            "skipped_decision_count": self.skipped_decision_count,
            "selected_statistics_context_count": self.selected_statistics_context_count,
            "statistics_observation_count": self.statistics_observation_count,
            "strategy_teacher_evidence_count": self.strategy_teacher_evidence_count,
            "commentary_evidence_count": self.commentary_evidence_count,
            "response_evidence_count": self.response_evidence_count,
            "records_with_strategy_teacher_count": self.records_with_strategy_teacher_count,
            "records_with_commentary_count": self.records_with_commentary_count,
            "records_with_outgoing_response_count": (
                self.records_with_outgoing_response_count
            ),
            "records_with_incoming_response_count": (
                self.records_with_incoming_response_count
            ),
            "unjoined_commentary_evidence_count": self.unjoined_commentary_evidence_count,
            "unjoined_response_evidence_count": self.unjoined_response_evidence_count,
            "records": [item.to_dict() for item in self.records],
            "skipped_decisions": [item.to_dict() for item in self.skipped_decisions],
            "player_statistics_observations": [
                item.to_dict() for item in self.player_statistics_observations
            ],
            "strategy_teacher_evidences": [
                item.to_dict() for item in self.strategy_teacher_evidences
            ],
            "commentary_evidences": [item.to_dict() for item in self.commentary_evidences],
            "response_evidences": [item.to_dict() for item in self.response_evidences],
            "unjoined_commentary_evidence_ids": list(
                self.unjoined_commentary_evidence_ids
            ),
            "unjoined_response_evidence_ids": list(self.unjoined_response_evidence_ids),
        }


def _dataset_fingerprint_material(value: LearningDatasetV2) -> dict[str, Any]:
    material = value.to_dict()
    del material["dataset_fingerprint"]
    return material


def _build_learning_dataset_v2(**values: Any) -> LearningDatasetV2:
    provisional = LearningDatasetV2._from_validated(
        dataset_fingerprint="0" * 64,
        **values,
    )
    return LearningDatasetV2._from_validated(
        dataset_fingerprint=_build_identifier(
            _DATASET_FINGERPRINT_DOMAIN,
            _dataset_fingerprint_material(provisional),
        ),
        **values,
    )


def _validate_learning_dataset_v2(dataset: LearningDatasetV2) -> None:
    if type(dataset) is not LearningDatasetV2:
        raise ValueError("dataset must be an exact LearningDatasetV2.")
    dataset._validate(verify_fingerprint=True, validate_nested=True)
