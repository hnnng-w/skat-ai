from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Final

from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
    validate_game_declaration,
)
from skat_ai.learning_corpus_identity import (
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)

LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION = 1
LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION = 1
LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION = 1
LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION = 1

LEARNING_CORPUS_HUMAN_EVIDENCE_KINDS: Final[tuple[str, ...]] = (
    "commentary",
    "linked_response",
)
LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS: Final[tuple[str, ...]] = (
    "match_player",
    "external",
    "match_player_and_external",
)

LEARNING_CORPUS_HUMAN_EVIDENCE_SOURCE_POLICY = "explicit_current_match_snapshots_only"
LEARNING_CORPUS_HUMAN_TEXT_POLICY = "preserve_exact_human_text_without_normalization_or_taxonomy"
LEARNING_CORPUS_RESPONSE_RELATION_POLICY = (
    "caller_linked_later_observed_decision_without_causal_claim"
)
LEARNING_CORPUS_OBSERVED_BEHAVIOR_POLICY = "actual_cards_are_observed_behavior_not_optimal_labels"
LEARNING_CORPUS_MEDIA_CONTEXT_POLICY = "retain_descriptive_source_metadata_and_exact_timecodes"
LEARNING_CORPUS_DERIVED_TAG_POLICY = "no_derived_tags_in_version_1"
LEARNING_CORPUS_ANALYSIS_SEPARATION_POLICY = (
    "human_evidence_does_not_influence_analysis_search_or_coaching"
)
LEARNING_CORPUS_HUMAN_EVIDENCE_ORDER_POLICY = (
    "current_match_game_commentary_response_canonical_order"
)
LEARNING_CORPUS_HUMAN_EVIDENCE_PRIVACY_POLICY = "private_local_minimized_unredacted_human_evidence"

_COLLECTION_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_human_evidence_collection_v1\0"
_GAME_EVIDENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_human_evidence_game_v1\0"
_COMMENTARY_CONTENT_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_commentary_content_v1\0"
_COMMENTARY_EVIDENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_commentary_evidence_v1\0"
_RESPONSE_CONTENT_FINGERPRINT_DOMAIN = b"skat-ai\0learning_corpus_response_content_v1\0"
_RESPONSE_EVIDENCE_ID_DOMAIN = b"skat-ai\0learning_corpus_response_evidence_v1\0"

_VALID_CARDS = frozenset(get_full_deck())
_VALID_SEATS = ("forehand", "middlehand", "rearhand")
_VALID_ROLES = ("declarer", "defender")


def _build_identifier(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


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


def _require_non_negative_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _require_positive_integer(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_hash_tuple(value: tuple[str, ...], field_name: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be an immutable tuple.")
    for item in value:
        _require_hash(item, field_name)
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} must contain unique IDs.")


def _copy_timecode(value: MediaTimecodeV1 | None) -> MediaTimecodeV1 | None:
    if value is None:
        return None
    if type(value) is not MediaTimecodeV1:
        raise ValueError("Evidence timecodes must be exact MediaTimecodeV1 values.")
    return MediaTimecodeV1(
        media_timecode_version=value.media_timecode_version,
        start_offset_ms=value.start_offset_ms,
        end_offset_ms=value.end_offset_ms,
    )


def _copy_declaration(value: GameDeclaration | None) -> GameDeclaration | None:
    if value is None:
        return None
    if type(value) is not GameDeclaration:
        raise ValueError("declaration must be null or an exact GameDeclaration.")
    return GameDeclaration(
        game_type=value.game_type,
        hand_game=value.hand_game,
        ouvert=value.ouvert,
        schneider_announced=value.schneider_announced,
        schwarz_announced=value.schwarz_announced,
        matadors=value.matadors,
        bid_value=value.bid_value,
    )


def build_learning_corpus_commentary_content_fingerprint_v1(
    commentary: ObservedDecisionCommentaryV1,
) -> str:
    """Fingerprints one exact original source Commentary value."""
    if type(commentary) is not ObservedDecisionCommentaryV1:
        raise ValueError("commentary must be an exact ObservedDecisionCommentaryV1.")
    reconstructed = ObservedDecisionCommentaryV1(
        decision_commentary_version=commentary.decision_commentary_version,
        commentary_id=commentary.commentary_id,
        decision_index=commentary.decision_index,
        subject_player_id=commentary.subject_player_id,
        commentator_player_id=commentary.commentator_player_id,
        commentator_name=commentary.commentator_name,
        text=commentary.text,
        commentary_timecode=commentary.commentary_timecode,
    )
    return _build_identifier(
        _COMMENTARY_CONTENT_FINGERPRINT_DOMAIN,
        reconstructed.to_dict(),
    )


def build_learning_corpus_response_content_fingerprint_v1(
    response_link: ObservedDecisionResponseLinkV1,
) -> str:
    """Fingerprints one exact original source Response Link value."""
    if type(response_link) is not ObservedDecisionResponseLinkV1:
        raise ValueError("response_link must be an exact ObservedDecisionResponseLinkV1.")
    reconstructed = ObservedDecisionResponseLinkV1(
        decision_response_link_version=response_link.decision_response_link_version,
        link_id=response_link.link_id,
        commentary_id=response_link.commentary_id,
        response_decision_index=response_link.response_decision_index,
    )
    return _build_identifier(
        _RESPONSE_CONTENT_FINGERPRINT_DOMAIN,
        reconstructed.to_dict(),
    )


def _build_game_evidence_id_v1(
    *,
    match_snapshot_id: str,
    game_reference_id: str,
    game_content_fingerprint: str,
) -> str:
    return _build_identifier(
        _GAME_EVIDENCE_ID_DOMAIN,
        {
            "learning_corpus_human_evidence_game_version": (
                LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION
            ),
            "match_snapshot_id": match_snapshot_id,
            "game_reference_id": game_reference_id,
            "game_content_fingerprint": game_content_fingerprint,
        },
    )


def _build_commentary_evidence_id_v1(
    *,
    commentary_content_fingerprint: str,
    commentary_reference_id: str,
    game_evidence_id: str,
) -> str:
    return _build_identifier(
        _COMMENTARY_EVIDENCE_ID_DOMAIN,
        {
            "learning_corpus_commentary_evidence_version": (
                LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION
            ),
            "game_evidence_id": game_evidence_id,
            "commentary_reference_id": commentary_reference_id,
            "commentary_content_fingerprint": commentary_content_fingerprint,
        },
    )


def _build_response_evidence_id_v1(
    *,
    response_content_fingerprint: str,
    response_reference_id: str,
    game_evidence_id: str,
) -> str:
    return _build_identifier(
        _RESPONSE_EVIDENCE_ID_DOMAIN,
        {
            "learning_corpus_response_evidence_version": (
                LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION
            ),
            "game_evidence_id": game_evidence_id,
            "response_reference_id": response_reference_id,
            "response_content_fingerprint": response_content_fingerprint,
        },
    )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusHumanEvidenceGameV1:
    """Minimized source and Game context for one Game containing Commentary."""

    learning_corpus_human_evidence_game_version: int = LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION
    game_evidence_id: str
    match_snapshot_id: str
    game_reference_id: str
    game_content_fingerprint: str
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
    perspective_player_id: str
    forehand_player_id: str
    middlehand_player_id: str
    rearhand_player_id: str
    declarer_player_id: str
    declaration: GameDeclaration | None
    decision_count: int
    commentary_evidence_ids: tuple[str, ...]
    response_evidence_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusHumanEvidenceGameV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningCorpusHumanEvidenceGameV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_human_evidence_game_version",
            LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in {"match_timecode", "game_timecode"}:
                field_value = _copy_timecode(field_value)
            elif field_name == "declaration":
                field_value = _copy_declaration(field_value)
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_human_evidence_game_version,
            LEARNING_CORPUS_HUMAN_EVIDENCE_GAME_VERSION,
            "learning_corpus_human_evidence_game_version",
        )
        for field_name in (
            "game_evidence_id",
            "match_snapshot_id",
            "game_reference_id",
            "game_content_fingerprint",
        ):
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
        _require_non_negative_integer(self.workspace_revision, "workspace_revision")
        if type(self.match_position) is not int or not 1 <= self.match_position <= 36:
            raise ValueError("match_position must be an integer from 1 through 36.")
        if type(self.match_timecode) not in {MediaTimecodeV1, type(None)}:
            raise ValueError("match_timecode must be null or MediaTimecodeV1.")
        if type(self.game_timecode) not in {MediaTimecodeV1, type(None)}:
            raise ValueError("game_timecode must be null or MediaTimecodeV1.")
        seat_players = (
            self.forehand_player_id,
            self.middlehand_player_id,
            self.rearhand_player_id,
        )
        if len(set(seat_players)) != 3:
            raise ValueError("Game Evidence seats must contain three unique Players.")
        if self.perspective_player_id not in seat_players:
            raise ValueError("Perspective Player must belong to the Game.")
        if self.declarer_player_id not in seat_players:
            raise ValueError("Declarer must belong to the Game.")
        if self.declaration is not None:
            validate_game_declaration(self.declaration)
        _require_positive_integer(self.decision_count, "decision_count")
        _require_hash_tuple(self.commentary_evidence_ids, "commentary_evidence_ids")
        _require_hash_tuple(self.response_evidence_ids, "response_evidence_ids")
        if not self.commentary_evidence_ids:
            raise ValueError("Game Evidence requires at least one Commentary item.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_human_evidence_game_version": (
                self.learning_corpus_human_evidence_game_version
            ),
            "game_evidence_id": self.game_evidence_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "game_content_fingerprint": self.game_content_fingerprint,
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
            "match_timecode": (
                None if self.match_timecode is None else self.match_timecode.to_dict()
            ),
            "game_timecode": (None if self.game_timecode is None else self.game_timecode.to_dict()),
            "perspective_player_id": self.perspective_player_id,
            "forehand_player_id": self.forehand_player_id,
            "middlehand_player_id": self.middlehand_player_id,
            "rearhand_player_id": self.rearhand_player_id,
            "declarer_player_id": self.declarer_player_id,
            "declaration": (
                None
                if self.declaration is None
                else build_serializable_game_declaration(self.declaration)
            ),
            "decision_count": self.decision_count,
            "commentary_evidence_ids": list(self.commentary_evidence_ids),
            "response_evidence_ids": list(self.response_evidence_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusCommentaryEvidenceV1:
    """Exact original human Commentary plus its observed subject behavior."""

    learning_corpus_commentary_evidence_version: int = LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION
    commentary_evidence_id: str
    commentary_content_fingerprint: str
    commentary_reference_id: str
    game_evidence_id: str
    match_snapshot_id: str
    game_reference_id: str
    commentary_id: str
    subject_decision_reference_id: str
    subject_decision_index: int
    subject_trick_number: int
    subject_play_index: int
    subject_player_id: str
    subject_player_label: str | None
    subject_seat: str
    subject_role: str
    actual_card_played: str
    decision_timecode: MediaTimecodeV1 | None
    commentary_timecode: MediaTimecodeV1 | None
    commentator_identity_kind: str
    commentator_player_id: str | None
    commentator_name: str | None
    text: str
    response_evidence_ids: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusCommentaryEvidenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningCorpusCommentaryEvidenceV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_commentary_evidence_version",
            LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name in {"decision_timecode", "commentary_timecode"}:
                field_value = _copy_timecode(field_value)
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_commentary_evidence_version,
            LEARNING_CORPUS_COMMENTARY_EVIDENCE_VERSION,
            "learning_corpus_commentary_evidence_version",
        )
        for field_name in (
            "commentary_evidence_id",
            "commentary_content_fingerprint",
            "commentary_reference_id",
            "game_evidence_id",
            "match_snapshot_id",
            "game_reference_id",
            "subject_decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in (
            "subject_decision_index",
            "subject_trick_number",
            "subject_play_index",
        ):
            _require_positive_integer(getattr(self, field_name), field_name)
        if self.subject_trick_number != ((self.subject_decision_index - 1) // 3) + 1:
            raise ValueError("subject_trick_number must match the Decision index.")
        if self.subject_play_index != ((self.subject_decision_index - 1) % 3) + 1:
            raise ValueError("subject_play_index must match the Decision index.")
        _require_identifier(self.subject_player_id, "subject_player_id")
        _require_identifier(self.commentary_id, "commentary_id")
        _require_identifier(
            self.subject_player_label,
            "subject_player_label",
            allow_none=True,
        )
        if self.subject_seat not in _VALID_SEATS:
            raise ValueError("subject_seat must be one canonical historical seat.")
        if self.subject_role not in _VALID_ROLES:
            raise ValueError("subject_role must be declarer or defender.")
        if self.actual_card_played not in _VALID_CARDS:
            raise ValueError("actual_card_played must be one valid Skat Card.")
        if self.commentator_identity_kind not in (LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS):
            raise ValueError("commentator_identity_kind must be canonical.")
        _require_identifier(
            self.commentator_player_id,
            "commentator_player_id",
            allow_none=True,
        )
        _require_identifier(
            self.commentator_name,
            "commentator_name",
            allow_none=True,
        )
        if self.commentator_player_id is None and self.commentator_name is None:
            raise ValueError("At least one commentator identity is required.")
        expected_kind = (
            LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[2]
            if self.commentator_player_id is not None and self.commentator_name is not None
            else LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[0]
            if self.commentator_player_id is not None
            else LEARNING_CORPUS_COMMENTATOR_IDENTITY_KINDS[1]
        )
        if self.commentator_identity_kind != expected_kind:
            raise ValueError("Commentator identity kind must match exact source identity.")
        _require_identifier(self.text, "text")
        _require_hash_tuple(self.response_evidence_ids, "response_evidence_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_commentary_evidence_version": (
                self.learning_corpus_commentary_evidence_version
            ),
            "commentary_evidence_id": self.commentary_evidence_id,
            "commentary_content_fingerprint": self.commentary_content_fingerprint,
            "commentary_reference_id": self.commentary_reference_id,
            "game_evidence_id": self.game_evidence_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "commentary_id": self.commentary_id,
            "subject_decision_reference_id": self.subject_decision_reference_id,
            "subject_decision_index": self.subject_decision_index,
            "subject_trick_number": self.subject_trick_number,
            "subject_play_index": self.subject_play_index,
            "subject_player_id": self.subject_player_id,
            "subject_player_label": self.subject_player_label,
            "subject_seat": self.subject_seat,
            "subject_role": self.subject_role,
            "actual_card_played": self.actual_card_played,
            "decision_timecode": (
                None if self.decision_timecode is None else self.decision_timecode.to_dict()
            ),
            "commentary_timecode": (
                None if self.commentary_timecode is None else self.commentary_timecode.to_dict()
            ),
            "commentator_identity_kind": self.commentator_identity_kind,
            "commentator_player_id": self.commentator_player_id,
            "commentator_name": self.commentator_name,
            "text": self.text,
            "response_evidence_ids": list(self.response_evidence_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusResponseEvidenceV1:
    """One factual observed behavior linked by a caller-authored association."""

    learning_corpus_response_evidence_version: int = LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION
    response_evidence_id: str
    response_content_fingerprint: str
    response_reference_id: str
    game_evidence_id: str
    match_snapshot_id: str
    game_reference_id: str
    link_id: str
    commentary_evidence_id: str
    commentary_reference_id: str
    subject_decision_reference_id: str
    subject_decision_index: int
    response_decision_reference_id: str
    response_decision_index: int
    response_trick_number: int
    response_play_index: int
    response_player_id: str
    response_player_label: str | None
    response_seat: str
    response_role: str
    response_card_played: str
    response_decision_timecode: MediaTimecodeV1 | None
    decision_offset: int
    same_trick: bool

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusResponseEvidenceV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(cls, **values: Any) -> LearningCorpusResponseEvidenceV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_response_evidence_version",
            LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION,
        )
        for field_name, field_value in values.items():
            if field_name == "response_decision_timecode":
                field_value = _copy_timecode(field_value)
            object.__setattr__(value, field_name, field_value)
        value._validate()
        return value

    def _validate(self) -> None:
        _require_version(
            self.learning_corpus_response_evidence_version,
            LEARNING_CORPUS_RESPONSE_EVIDENCE_VERSION,
            "learning_corpus_response_evidence_version",
        )
        for field_name in (
            "response_evidence_id",
            "response_content_fingerprint",
            "response_reference_id",
            "game_evidence_id",
            "match_snapshot_id",
            "game_reference_id",
            "commentary_evidence_id",
            "commentary_reference_id",
            "subject_decision_reference_id",
            "response_decision_reference_id",
        ):
            _require_hash(getattr(self, field_name), field_name)
        for field_name in (
            "subject_decision_index",
            "response_decision_index",
            "response_trick_number",
            "response_play_index",
            "decision_offset",
        ):
            _require_positive_integer(getattr(self, field_name), field_name)
        if self.response_decision_index <= self.subject_decision_index:
            raise ValueError("A Response Decision must be later than its subject.")
        if self.decision_offset != (self.response_decision_index - self.subject_decision_index):
            raise ValueError("decision_offset must equal the positive Decision difference.")
        expected_trick = ((self.response_decision_index - 1) // 3) + 1
        expected_play = ((self.response_decision_index - 1) % 3) + 1
        if self.response_trick_number != expected_trick:
            raise ValueError("response_trick_number must match the Decision index.")
        if self.response_play_index != expected_play:
            raise ValueError("response_play_index must match the Decision index.")
        _require_identifier(self.response_player_id, "response_player_id")
        _require_identifier(self.link_id, "link_id")
        _require_identifier(
            self.response_player_label,
            "response_player_label",
            allow_none=True,
        )
        if self.response_seat not in _VALID_SEATS:
            raise ValueError("response_seat must be one canonical historical seat.")
        if self.response_role not in _VALID_ROLES:
            raise ValueError("response_role must be declarer or defender.")
        if self.response_card_played not in _VALID_CARDS:
            raise ValueError("response_card_played must be one valid Skat Card.")
        if type(self.same_trick) is not bool:
            raise ValueError("same_trick must be a boolean.")
        subject_trick = ((self.subject_decision_index - 1) // 3) + 1
        if self.same_trick != (subject_trick == self.response_trick_number):
            raise ValueError("same_trick must be the factual Trick-index comparison.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_response_evidence_version": (
                self.learning_corpus_response_evidence_version
            ),
            "response_evidence_id": self.response_evidence_id,
            "response_content_fingerprint": self.response_content_fingerprint,
            "response_reference_id": self.response_reference_id,
            "game_evidence_id": self.game_evidence_id,
            "match_snapshot_id": self.match_snapshot_id,
            "game_reference_id": self.game_reference_id,
            "link_id": self.link_id,
            "commentary_evidence_id": self.commentary_evidence_id,
            "commentary_reference_id": self.commentary_reference_id,
            "subject_decision_reference_id": self.subject_decision_reference_id,
            "subject_decision_index": self.subject_decision_index,
            "response_decision_reference_id": self.response_decision_reference_id,
            "response_decision_index": self.response_decision_index,
            "response_trick_number": self.response_trick_number,
            "response_play_index": self.response_play_index,
            "response_player_id": self.response_player_id,
            "response_player_label": self.response_player_label,
            "response_seat": self.response_seat,
            "response_role": self.response_role,
            "response_card_played": self.response_card_played,
            "response_decision_timecode": (
                None
                if self.response_decision_timecode is None
                else self.response_decision_timecode.to_dict()
            ),
            "decision_offset": self.decision_offset,
            "same_trick": self.same_trick,
        }


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusHumanEvidenceCollectionV1:
    """One deterministic flattened Human Evidence view over Current Matches."""

    learning_corpus_human_evidence_version: int = LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION
    human_evidence_collection_fingerprint: str
    corpus_id: str
    source_catalog_revision: int
    source_catalog_fingerprint: str
    source_catalog_content_fingerprint: str
    current_match_snapshot_ids: tuple[str, ...]
    retained_match_snapshot_count: int
    current_match_count: int
    orphan_match_snapshot_count: int
    observed_game_count: int
    evidence_game_count: int
    decision_count: int
    commented_decision_count: int
    commentary_count: int
    response_count: int
    games: tuple[LearningCorpusHumanEvidenceGameV1, ...]
    commentaries: tuple[LearningCorpusCommentaryEvidenceV1, ...]
    responses: tuple[LearningCorpusResponseEvidenceV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusHumanEvidenceCollectionV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        **values: Any,
    ) -> LearningCorpusHumanEvidenceCollectionV1:
        value = object.__new__(cls)
        object.__setattr__(
            value,
            "learning_corpus_human_evidence_version",
            LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION,
        )
        for field_name, field_value in values.items():
            object.__setattr__(value, field_name, field_value)
        value._validate(verify_fingerprint=False)
        return value

    def _validate(self, *, verify_fingerprint: bool) -> None:
        _require_version(
            self.learning_corpus_human_evidence_version,
            LEARNING_CORPUS_HUMAN_EVIDENCE_VERSION,
            "learning_corpus_human_evidence_version",
        )
        _require_hash(
            self.human_evidence_collection_fingerprint,
            "human_evidence_collection_fingerprint",
        )
        _require_identifier(self.corpus_id, "corpus_id")
        _require_non_negative_integer(
            self.source_catalog_revision,
            "source_catalog_revision",
        )
        _require_hash(self.source_catalog_fingerprint, "source_catalog_fingerprint")
        _require_hash(
            self.source_catalog_content_fingerprint,
            "source_catalog_content_fingerprint",
        )
        _require_hash_tuple(
            self.current_match_snapshot_ids,
            "current_match_snapshot_ids",
        )
        for field_name in (
            "retained_match_snapshot_count",
            "current_match_count",
            "orphan_match_snapshot_count",
            "observed_game_count",
            "evidence_game_count",
            "decision_count",
            "commented_decision_count",
            "commentary_count",
            "response_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.current_match_count != len(self.current_match_snapshot_ids):
            raise ValueError("current_match_count must reconcile exactly.")
        if self.retained_match_snapshot_count < self.current_match_count:
            raise ValueError("Retained Snapshot count cannot be below Current count.")
        for field_name, expected_type in (
            ("games", LearningCorpusHumanEvidenceGameV1),
            ("commentaries", LearningCorpusCommentaryEvidenceV1),
            ("responses", LearningCorpusResponseEvidenceV1),
        ):
            values = getattr(self, field_name)
            if type(values) is not tuple:
                raise ValueError(f"{field_name} must be an immutable tuple.")
            for item in values:
                if type(item) is not expected_type:
                    raise ValueError(f"{field_name} contains an invalid evidence value.")
                item._validate()

        if self.games != tuple(
            sorted(
                self.games,
                key=lambda item: (
                    item.match_id,
                    item.match_position,
                    item.game_reference_id,
                ),
            )
        ):
            raise ValueError("Game Evidence must use Current Match and position order.")
        games_by_id = {item.game_evidence_id: item for item in self.games}
        if len(games_by_id) != len(self.games):
            raise ValueError("Game Evidence IDs must be unique.")
        if len({item.game_reference_id for item in self.games}) != len(self.games):
            raise ValueError("Game Reference IDs must be unique in one collection.")
        if any(
            item.match_snapshot_id not in self.current_match_snapshot_ids for item in self.games
        ):
            raise ValueError("Game Evidence must belong to a Current Match Snapshot.")

        commentaries_by_id = {item.commentary_evidence_id: item for item in self.commentaries}
        responses_by_id = {item.response_evidence_id: item for item in self.responses}
        if len(commentaries_by_id) != len(self.commentaries):
            raise ValueError("Commentary Evidence IDs must be unique.")
        if len(responses_by_id) != len(self.responses):
            raise ValueError("Response Evidence IDs must be unique.")
        if len({item.commentary_reference_id for item in self.commentaries}) != len(
            self.commentaries
        ):
            raise ValueError("Commentary References must be unique in one collection.")
        if len({item.response_reference_id for item in self.responses}) != len(self.responses):
            raise ValueError("Response References must be unique in one collection.")

        expected_commentary_ids = tuple(
            evidence_id for game in self.games for evidence_id in game.commentary_evidence_ids
        )
        expected_response_ids = tuple(
            evidence_id for game in self.games for evidence_id in game.response_evidence_ids
        )
        if tuple(item.commentary_evidence_id for item in self.commentaries) != (
            expected_commentary_ids
        ):
            raise ValueError("Flattened Commentary Evidence order must reconcile.")
        if tuple(item.response_evidence_id for item in self.responses) != (expected_response_ids):
            raise ValueError("Flattened Response Evidence order must reconcile.")

        responses_by_commentary: dict[str, list[str]] = {
            evidence_id: [] for evidence_id in commentaries_by_id
        }
        for commentary in self.commentaries:
            game = games_by_id.get(commentary.game_evidence_id)
            if game is None:
                raise ValueError("Commentary Evidence requires its parent Game Evidence.")
            if (
                commentary.commentary_evidence_id not in game.commentary_evidence_ids
                or commentary.match_snapshot_id != game.match_snapshot_id
                or commentary.game_reference_id != game.game_reference_id
            ):
                raise ValueError("Commentary Evidence must reconcile with its parent Game.")
        for response in self.responses:
            game = games_by_id.get(response.game_evidence_id)
            commentary = commentaries_by_id.get(response.commentary_evidence_id)
            if game is None or commentary is None:
                raise ValueError("Response Evidence requires its Game and Commentary parents.")
            if commentary.game_evidence_id != response.game_evidence_id:
                raise ValueError("Response and Commentary Evidence must use the same Game.")
            if (
                response.response_evidence_id not in game.response_evidence_ids
                or response.match_snapshot_id != game.match_snapshot_id
                or response.game_reference_id != game.game_reference_id
                or response.match_snapshot_id != commentary.match_snapshot_id
                or response.game_reference_id != commentary.game_reference_id
                or commentary.commentary_reference_id != response.commentary_reference_id
                or commentary.subject_decision_reference_id
                != response.subject_decision_reference_id
                or commentary.subject_decision_index != response.subject_decision_index
            ):
                raise ValueError("Response Evidence must reconcile with source Commentary.")
            responses_by_commentary[response.commentary_evidence_id].append(
                response.response_evidence_id
            )
        for commentary in self.commentaries:
            if commentary.response_evidence_ids != tuple(
                responses_by_commentary[commentary.commentary_evidence_id]
            ):
                raise ValueError("Commentary Response child IDs must reconcile.")

        if self.evidence_game_count != len(self.games):
            raise ValueError("evidence_game_count must reconcile exactly.")
        if self.commentary_count != len(self.commentaries):
            raise ValueError("commentary_count must reconcile exactly.")
        if self.response_count != len(self.responses):
            raise ValueError("response_count must reconcile exactly.")
        distinct_subjects = {item.subject_decision_reference_id for item in self.commentaries}
        if self.commented_decision_count != len(distinct_subjects):
            raise ValueError("commented_decision_count must count distinct Decisions.")
        if self.observed_game_count < self.evidence_game_count:
            raise ValueError("Evidence Game count cannot exceed Current observed Games.")
        if self.decision_count < sum(item.decision_count for item in self.games):
            raise ValueError("Evidence Game Decisions exceed Current observed Decisions.")
        if self.decision_count < self.commented_decision_count:
            raise ValueError("Commented Decisions exceed Current observed Decisions.")
        if verify_fingerprint:
            expected = _build_identifier(
                _COLLECTION_FINGERPRINT_DOMAIN,
                _collection_fingerprint_material_v1(self),
            )
            if self.human_evidence_collection_fingerprint != expected:
                raise ValueError(
                    "human_evidence_collection_fingerprint must cover the exact collection."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_human_evidence_version": (self.learning_corpus_human_evidence_version),
            "human_evidence_collection_fingerprint": (self.human_evidence_collection_fingerprint),
            "corpus_id": self.corpus_id,
            "source_catalog_revision": self.source_catalog_revision,
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "source_catalog_content_fingerprint": (self.source_catalog_content_fingerprint),
            "current_match_snapshot_ids": list(self.current_match_snapshot_ids),
            "retained_match_snapshot_count": self.retained_match_snapshot_count,
            "current_match_count": self.current_match_count,
            "orphan_match_snapshot_count": self.orphan_match_snapshot_count,
            "observed_game_count": self.observed_game_count,
            "evidence_game_count": self.evidence_game_count,
            "decision_count": self.decision_count,
            "commented_decision_count": self.commented_decision_count,
            "commentary_count": self.commentary_count,
            "response_count": self.response_count,
            "games": [item.to_dict() for item in self.games],
            "commentaries": [item.to_dict() for item in self.commentaries],
            "responses": [item.to_dict() for item in self.responses],
        }


def _collection_fingerprint_material_v1(
    collection: LearningCorpusHumanEvidenceCollectionV1,
) -> dict[str, Any]:
    material = collection.to_dict()
    del material["human_evidence_collection_fingerprint"]
    return material


def _build_collection_fingerprint_v1(value: object) -> str:
    return _build_identifier(_COLLECTION_FINGERPRINT_DOMAIN, value)


def _validate_learning_corpus_human_evidence_collection_v1(
    collection: LearningCorpusHumanEvidenceCollectionV1,
) -> None:
    if type(collection) is not LearningCorpusHumanEvidenceCollectionV1:
        raise ValueError("collection must be an exact LearningCorpusHumanEvidenceCollectionV1.")
    collection._validate(verify_fingerprint=True)
