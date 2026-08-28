from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skatmind.learning_corpus_identity import (
    _build_commentary_reference_id_v1,
    _build_decision_reference_id_v1,
    _build_game_content_fingerprint_v1,
    _build_game_reference_id_v1,
    _build_player_observation_id_v1,
    _build_response_reference_id_v1,
)
from skatmind.observed_game_contracts import ObservedGameRecordV1

LEARNING_CORPUS_REFERENCE_VERSION = 1


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
    return value


def _require_hash(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hexadecimal value.")
    return value


def _require_match_position(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 36:
        raise ValueError("match_position must be an integer from 1 through 36.")
    return value


def _require_positive_decision_index(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("decision_index must be a positive integer.")
    return value


def _require_optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_identifier(value, field_name)


def _require_reference_ids(value: tuple[str, ...], field_name: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        _require_hash(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must not contain duplicate IDs.")


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusPlayerObservationV1:
    """One exact stable Match Player observation in one source Snapshot."""

    learning_corpus_reference_version: int = LEARNING_CORPUS_REFERENCE_VERSION
    player_observation_id: str
    match_snapshot_id: str
    player_id: str
    table_place: str
    player_label: str | None
    game_platform: str
    platform_player_id: str | None
    statistics_snapshot_id: str | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusPlayerObservationV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        player_observation_id: str,
        match_snapshot_id: str,
        player_id: str,
        table_place: str,
        player_label: str | None,
        game_platform: str,
        platform_player_id: str | None,
        statistics_snapshot_id: str | None,
    ) -> LearningCorpusPlayerObservationV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_reference_version", LEARNING_CORPUS_REFERENCE_VERSION),
            ("player_observation_id", player_observation_id),
            ("match_snapshot_id", match_snapshot_id),
            ("player_id", player_id),
            ("table_place", table_place),
            ("player_label", player_label),
            ("game_platform", game_platform),
            ("platform_player_id", platform_player_id),
            ("statistics_snapshot_id", statistics_snapshot_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_hash(self.player_observation_id, "player_observation_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_identifier(self.player_id, "player_id")
        _require_identifier(self.table_place, "table_place")
        _require_optional_identifier(self.player_label, "player_label")
        _require_identifier(self.game_platform, "game_platform")
        _require_optional_identifier(self.platform_player_id, "platform_player_id")
        _require_optional_identifier(
            self.statistics_snapshot_id,
            "statistics_snapshot_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_reference_version": self.learning_corpus_reference_version,
            "player_observation_id": self.player_observation_id,
            "match_snapshot_id": self.match_snapshot_id,
            "player_id": self.player_id,
            "table_place": self.table_place,
            "player_label": self.player_label,
            "game_platform": self.game_platform,
            "platform_player_id": self.platform_player_id,
            "statistics_snapshot_id": self.statistics_snapshot_id,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusGameReferenceV1:
    """One Snapshot-scoped reference to one retained observed Game."""

    learning_corpus_reference_version: int = LEARNING_CORPUS_REFERENCE_VERSION
    game_reference_id: str
    game_content_fingerprint: str
    match_snapshot_id: str
    match_id: str
    match_position: int
    game_id: str
    decision_reference_ids: tuple[str, ...]
    commentary_reference_ids: tuple[str, ...]
    response_reference_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusGameReferenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        game_reference_id: str,
        game_content_fingerprint: str,
        match_snapshot_id: str,
        match_id: str,
        match_position: int,
        game_id: str,
        decision_reference_ids: tuple[str, ...],
        commentary_reference_ids: tuple[str, ...],
        response_reference_ids: tuple[str, ...],
    ) -> LearningCorpusGameReferenceV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_reference_version", LEARNING_CORPUS_REFERENCE_VERSION),
            ("game_reference_id", game_reference_id),
            ("game_content_fingerprint", game_content_fingerprint),
            ("match_snapshot_id", match_snapshot_id),
            ("match_id", match_id),
            ("match_position", match_position),
            ("game_id", game_id),
            ("decision_reference_ids", decision_reference_ids),
            ("commentary_reference_ids", commentary_reference_ids),
            ("response_reference_ids", response_reference_ids),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_hash(self.game_reference_id, "game_reference_id")
        _require_hash(self.game_content_fingerprint, "game_content_fingerprint")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_identifier(self.match_id, "match_id")
        _require_match_position(self.match_position)
        _require_identifier(self.game_id, "game_id")
        _require_reference_ids(self.decision_reference_ids, "decision_reference_ids")
        _require_reference_ids(self.commentary_reference_ids, "commentary_reference_ids")
        _require_reference_ids(self.response_reference_ids, "response_reference_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_reference_version": self.learning_corpus_reference_version,
            "game_reference_id": self.game_reference_id,
            "game_content_fingerprint": self.game_content_fingerprint,
            "match_snapshot_id": self.match_snapshot_id,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "decision_reference_ids": list(self.decision_reference_ids),
            "commentary_reference_ids": list(self.commentary_reference_ids),
            "response_reference_ids": list(self.response_reference_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusDecisionReferenceV1:
    """One Snapshot-scoped identity for one retained observed Play."""

    learning_corpus_reference_version: int = LEARNING_CORPUS_REFERENCE_VERSION
    decision_reference_id: str
    match_snapshot_id: str
    game_reference_id: str
    match_id: str
    game_id: str
    match_position: int
    decision_index: int
    acting_player_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusDecisionReferenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        decision_reference_id: str,
        match_snapshot_id: str,
        game_reference_id: str,
        match_id: str,
        game_id: str,
        match_position: int,
        decision_index: int,
        acting_player_id: str,
    ) -> LearningCorpusDecisionReferenceV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_reference_version", LEARNING_CORPUS_REFERENCE_VERSION),
            ("decision_reference_id", decision_reference_id),
            ("match_snapshot_id", match_snapshot_id),
            ("game_reference_id", game_reference_id),
            ("match_id", match_id),
            ("game_id", game_id),
            ("match_position", match_position),
            ("decision_index", decision_index),
            ("acting_player_id", acting_player_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_hash(self.decision_reference_id, "decision_reference_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_hash(self.game_reference_id, "game_reference_id")
        _require_identifier(self.match_id, "match_id")
        _require_identifier(self.game_id, "game_id")
        _require_match_position(self.match_position)
        _require_positive_decision_index(self.decision_index)
        _require_identifier(self.acting_player_id, "acting_player_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_reference_version": self.learning_corpus_reference_version,
            "decision_reference_id": self.decision_reference_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "match_id": self.match_id,
            "game_id": self.game_id,
            "match_position": self.match_position,
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusCommentaryReferenceV1:
    """One Snapshot-scoped reference to retained original Commentary."""

    learning_corpus_reference_version: int = LEARNING_CORPUS_REFERENCE_VERSION
    commentary_reference_id: str
    match_snapshot_id: str
    game_reference_id: str
    commentary_id: str
    subject_decision_reference_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusCommentaryReferenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        commentary_reference_id: str,
        match_snapshot_id: str,
        game_reference_id: str,
        commentary_id: str,
        subject_decision_reference_id: str,
    ) -> LearningCorpusCommentaryReferenceV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_reference_version", LEARNING_CORPUS_REFERENCE_VERSION),
            ("commentary_reference_id", commentary_reference_id),
            ("match_snapshot_id", match_snapshot_id),
            ("game_reference_id", game_reference_id),
            ("commentary_id", commentary_id),
            ("subject_decision_reference_id", subject_decision_reference_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_hash(self.commentary_reference_id, "commentary_reference_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_hash(self.game_reference_id, "game_reference_id")
        _require_identifier(self.commentary_id, "commentary_id")
        _require_hash(
            self.subject_decision_reference_id,
            "subject_decision_reference_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_reference_version": self.learning_corpus_reference_version,
            "commentary_reference_id": self.commentary_reference_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "commentary_id": self.commentary_id,
            "subject_decision_reference_id": self.subject_decision_reference_id,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusResponseReferenceV1:
    """One closed Snapshot-scoped Commentary-to-Decision response reference."""

    learning_corpus_reference_version: int = LEARNING_CORPUS_REFERENCE_VERSION
    response_reference_id: str
    match_snapshot_id: str
    game_reference_id: str
    link_id: str
    commentary_reference_id: str
    response_decision_reference_id: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusResponseReferenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        response_reference_id: str,
        match_snapshot_id: str,
        game_reference_id: str,
        link_id: str,
        commentary_reference_id: str,
        response_decision_reference_id: str,
    ) -> LearningCorpusResponseReferenceV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            ("learning_corpus_reference_version", LEARNING_CORPUS_REFERENCE_VERSION),
            ("response_reference_id", response_reference_id),
            ("match_snapshot_id", match_snapshot_id),
            ("game_reference_id", game_reference_id),
            ("link_id", link_id),
            ("commentary_reference_id", commentary_reference_id),
            ("response_decision_reference_id", response_decision_reference_id),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_hash(self.response_reference_id, "response_reference_id")
        _require_hash(self.match_snapshot_id, "match_snapshot_id")
        _require_hash(self.game_reference_id, "game_reference_id")
        _require_identifier(self.link_id, "link_id")
        _require_hash(self.commentary_reference_id, "commentary_reference_id")
        _require_hash(
            self.response_decision_reference_id,
            "response_decision_reference_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_reference_version": self.learning_corpus_reference_version,
            "response_reference_id": self.response_reference_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "link_id": self.link_id,
            "commentary_reference_id": self.commentary_reference_id,
            "response_decision_reference_id": self.response_decision_reference_id,
        }


def build_learning_corpus_game_content_fingerprint_v1(
    observed_game: ObservedGameRecordV1,
    *,
    _legacy_identity: bool = False,
) -> str:
    """Fingerprints only one exact retained observed-Game document."""
    if type(observed_game) is not ObservedGameRecordV1:
        raise ValueError("observed_game must be an exact ObservedGameRecordV1.")
    return _build_game_content_fingerprint_v1(
        observed_game.to_dict(),
        legacy_identity=_legacy_identity,
    )


def _build_player_observation_v1(
    *,
    match_snapshot_id: str,
    player_id: str,
    table_place: str,
    player_label: str | None,
    game_platform: str,
    platform_player_id: str | None,
    statistics_snapshot_id: str | None,
    _legacy_identity: bool = False,
) -> LearningCorpusPlayerObservationV1:
    material = {
        "learning_corpus_reference_version": LEARNING_CORPUS_REFERENCE_VERSION,
        "match_snapshot_id": match_snapshot_id,
        "player_id": player_id,
        "table_place": table_place,
        "player_label": player_label,
        "game_platform": game_platform,
        "platform_player_id": platform_player_id,
        "statistics_snapshot_id": statistics_snapshot_id,
    }
    return LearningCorpusPlayerObservationV1._from_validated(
        player_observation_id=_build_player_observation_id_v1(
            material,
            legacy_identity=_legacy_identity,
        ),
        match_snapshot_id=match_snapshot_id,
        player_id=player_id,
        table_place=table_place,
        player_label=player_label,
        game_platform=game_platform,
        platform_player_id=platform_player_id,
        statistics_snapshot_id=statistics_snapshot_id,
    )


def _build_game_reference_identity_v1(
    *,
    game_content_fingerprint: str,
    match_snapshot_id: str,
    match_id: str,
    match_position: int,
    game_id: str,
    _legacy_identity: bool = False,
) -> str:
    return _build_game_reference_id_v1(
        {
            "learning_corpus_reference_version": LEARNING_CORPUS_REFERENCE_VERSION,
            "game_content_fingerprint": game_content_fingerprint,
            "match_snapshot_id": match_snapshot_id,
            "match_id": match_id,
            "match_position": match_position,
            "game_id": game_id,
        },
        legacy_identity=_legacy_identity,
    )


def _build_decision_reference_v1(
    *,
    match_snapshot_id: str,
    game_reference_id: str,
    match_id: str,
    game_id: str,
    match_position: int,
    decision_index: int,
    acting_player_id: str,
    _legacy_identity: bool = False,
) -> LearningCorpusDecisionReferenceV1:
    material = {
        "learning_corpus_reference_version": LEARNING_CORPUS_REFERENCE_VERSION,
        "match_snapshot_id": match_snapshot_id,
        "game_reference_id": game_reference_id,
        "match_id": match_id,
        "game_id": game_id,
        "match_position": match_position,
        "decision_index": decision_index,
        "acting_player_id": acting_player_id,
    }
    return LearningCorpusDecisionReferenceV1._from_validated(
        decision_reference_id=_build_decision_reference_id_v1(
            material,
            legacy_identity=_legacy_identity,
        ),
        match_snapshot_id=match_snapshot_id,
        game_reference_id=game_reference_id,
        match_id=match_id,
        game_id=game_id,
        match_position=match_position,
        decision_index=decision_index,
        acting_player_id=acting_player_id,
    )


def _build_commentary_reference_v1(
    *,
    match_snapshot_id: str,
    game_reference_id: str,
    commentary_id: str,
    subject_decision_reference_id: str,
    _legacy_identity: bool = False,
) -> LearningCorpusCommentaryReferenceV1:
    material = {
        "learning_corpus_reference_version": LEARNING_CORPUS_REFERENCE_VERSION,
        "match_snapshot_id": match_snapshot_id,
        "game_reference_id": game_reference_id,
        "commentary_id": commentary_id,
        "subject_decision_reference_id": subject_decision_reference_id,
    }
    return LearningCorpusCommentaryReferenceV1._from_validated(
        commentary_reference_id=_build_commentary_reference_id_v1(
            material,
            legacy_identity=_legacy_identity,
        ),
        match_snapshot_id=match_snapshot_id,
        game_reference_id=game_reference_id,
        commentary_id=commentary_id,
        subject_decision_reference_id=subject_decision_reference_id,
    )


def _build_response_reference_v1(
    *,
    match_snapshot_id: str,
    game_reference_id: str,
    link_id: str,
    commentary_reference_id: str,
    response_decision_reference_id: str,
    _legacy_identity: bool = False,
) -> LearningCorpusResponseReferenceV1:
    material = {
        "learning_corpus_reference_version": LEARNING_CORPUS_REFERENCE_VERSION,
        "match_snapshot_id": match_snapshot_id,
        "game_reference_id": game_reference_id,
        "link_id": link_id,
        "commentary_reference_id": commentary_reference_id,
        "response_decision_reference_id": response_decision_reference_id,
    }
    return LearningCorpusResponseReferenceV1._from_validated(
        response_reference_id=_build_response_reference_id_v1(
            material,
            legacy_identity=_legacy_identity,
        ),
        match_snapshot_id=match_snapshot_id,
        game_reference_id=game_reference_id,
        link_id=link_id,
        commentary_reference_id=commentary_reference_id,
        response_decision_reference_id=response_decision_reference_id,
    )
