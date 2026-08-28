from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.observed_game_trace import (
    ObservedPlayV1,
    _require_version,
    copy_observed_timecode_v1,
    validate_observed_player_id_v1,
    validate_observed_timecode_containment_v1,
)
from skatmind.performance_rating import (
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)

DECISION_COMMENTARY_VERSION = 1
DECISION_RESPONSE_LINK_VERSION = 1

DECISION_COMMENTARY_POLICY = "free_text_without_required_taxonomy"
DECISION_RESPONSE_LINK_POLICY = "later_observed_decision_reference"


def _require_positive_decision_index(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedDecisionCommentaryV1:
    """Authoritative caller free text attached to one observed decision."""

    decision_commentary_version: int = DECISION_COMMENTARY_VERSION
    commentary_id: str
    decision_index: int
    subject_player_id: str
    commentator_player_id: str | None
    commentator_name: str | None
    text: str
    commentary_timecode: MediaTimecodeV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.decision_commentary_version,
            DECISION_COMMENTARY_VERSION,
            "decision_commentary_version",
        )
        validate_stable_list_entry_identifier(self.commentary_id, "commentary_id")
        _require_positive_decision_index(self.decision_index, "decision_index")
        validate_observed_player_id_v1(self.subject_player_id, "subject_player_id")
        if self.commentator_player_id is not None:
            validate_observed_player_id_v1(
                self.commentator_player_id,
                "commentator_player_id",
            )
        if self.commentator_name is not None:
            validate_stable_list_player_label(self.commentator_name, "commentator_name")
        if self.commentator_player_id is None and self.commentator_name is None:
            raise ValueError("At least one commentator identity is required.")
        validate_stable_list_player_label(self.text, "text")
        object.__setattr__(
            self,
            "commentary_timecode",
            copy_observed_timecode_v1(self.commentary_timecode, "commentary_timecode"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_commentary_version": self.decision_commentary_version,
            "commentary_id": self.commentary_id,
            "decision_index": self.decision_index,
            "subject_player_id": self.subject_player_id,
            "commentator_player_id": self.commentator_player_id,
            "commentator_name": self.commentator_name,
            "text": self.text,
            "commentary_timecode": (
                None
                if self.commentary_timecode is None
                else self.commentary_timecode.to_dict()
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedDecisionResponseLinkV1:
    """One caller association from commentary to a later observed decision."""

    decision_response_link_version: int = DECISION_RESPONSE_LINK_VERSION
    link_id: str
    commentary_id: str
    response_decision_index: int

    def __post_init__(self) -> None:
        _require_version(
            self.decision_response_link_version,
            DECISION_RESPONSE_LINK_VERSION,
            "decision_response_link_version",
        )
        validate_stable_list_entry_identifier(self.link_id, "link_id")
        validate_stable_list_entry_identifier(self.commentary_id, "commentary_id")
        _require_positive_decision_index(
            self.response_decision_index,
            "response_decision_index",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_response_link_version": self.decision_response_link_version,
            "link_id": self.link_id,
            "commentary_id": self.commentary_id,
            "response_decision_index": self.response_decision_index,
        }


def _copy_commentary(value: ObservedDecisionCommentaryV1) -> ObservedDecisionCommentaryV1:
    if not isinstance(value, ObservedDecisionCommentaryV1):
        raise ValueError(
            "commentaries must contain only ObservedDecisionCommentaryV1 values."
        )
    return ObservedDecisionCommentaryV1(
        decision_commentary_version=value.decision_commentary_version,
        commentary_id=value.commentary_id,
        decision_index=value.decision_index,
        subject_player_id=value.subject_player_id,
        commentator_player_id=value.commentator_player_id,
        commentator_name=value.commentator_name,
        text=value.text,
        commentary_timecode=value.commentary_timecode,
    )


def _copy_response_link(
    value: ObservedDecisionResponseLinkV1,
) -> ObservedDecisionResponseLinkV1:
    if not isinstance(value, ObservedDecisionResponseLinkV1):
        raise ValueError(
            "response_links must contain only ObservedDecisionResponseLinkV1 values."
        )
    return ObservedDecisionResponseLinkV1(
        decision_response_link_version=value.decision_response_link_version,
        link_id=value.link_id,
        commentary_id=value.commentary_id,
        response_decision_index=value.response_decision_index,
    )


def canonicalize_observed_annotations_v1(
    *,
    commentaries: Sequence[ObservedDecisionCommentaryV1],
    response_links: Sequence[ObservedDecisionResponseLinkV1],
    plays: tuple[ObservedPlayV1, ...],
    game_player_ids: tuple[str, ...],
    game_timecode: MediaTimecodeV1 | None,
) -> tuple[
    tuple[ObservedDecisionCommentaryV1, ...],
    tuple[ObservedDecisionResponseLinkV1, ...],
]:
    """Validates references and returns canonical annotation order."""
    if isinstance(commentaries, (str, bytes)) or not isinstance(
        commentaries, (list, tuple)
    ):
        raise ValueError("commentaries must be an array.")
    retained_commentaries = tuple(_copy_commentary(item) for item in commentaries)
    commentary_ids = [item.commentary_id for item in retained_commentaries]
    if len(commentary_ids) != len(set(commentary_ids)):
        raise ValueError("commentary_id values must be unique within one observed Game.")

    plays_by_index = {play.decision_index: play for play in plays}
    player_ids = frozenset(game_player_ids)
    for item in retained_commentaries:
        play = plays_by_index.get(item.decision_index)
        if play is None:
            raise ValueError(
                f"Commentary '{item.commentary_id}' must reference one retained Play."
            )
        if item.subject_player_id != play.player_id:
            raise ValueError(
                f"Commentary '{item.commentary_id}' subject_player_id must match the "
                "referenced Play."
            )
        if (
            item.commentator_player_id is not None
            and item.commentator_player_id not in player_ids
        ):
            raise ValueError(
                f"Commentary '{item.commentary_id}' references an unknown commentator Player."
            )
        validate_observed_timecode_containment_v1(
            item.commentary_timecode,
            game_timecode,
            child_name=f"commentary '{item.commentary_id}' timecode",
            parent_name="game_timecode",
        )

    canonical_commentaries = tuple(
        sorted(
            retained_commentaries,
            key=lambda item: (
                item.decision_index,
                item.commentary_timecode is None,
                (
                    0
                    if item.commentary_timecode is None
                    else item.commentary_timecode.start_offset_ms
                ),
                item.commentary_id,
            ),
        )
    )
    commentary_by_id = {item.commentary_id: item for item in canonical_commentaries}
    commentary_order = {
        item.commentary_id: index for index, item in enumerate(canonical_commentaries)
    }

    if isinstance(response_links, (str, bytes)) or not isinstance(
        response_links, (list, tuple)
    ):
        raise ValueError("response_links must be an array.")
    retained_links = tuple(_copy_response_link(item) for item in response_links)
    link_ids = [item.link_id for item in retained_links]
    if len(link_ids) != len(set(link_ids)):
        raise ValueError("link_id values must be unique within one observed Game.")
    pairs: set[tuple[str, int]] = set()
    for item in retained_links:
        commentary = commentary_by_id.get(item.commentary_id)
        if commentary is None:
            raise ValueError(
                f"Response link '{item.link_id}' must reference retained commentary."
            )
        if item.response_decision_index not in plays_by_index:
            raise ValueError(
                f"Response link '{item.link_id}' must reference one retained response Play."
            )
        if item.response_decision_index <= commentary.decision_index:
            raise ValueError(
                f"Response link '{item.link_id}' must reference a later observed decision."
            )
        pair = (item.commentary_id, item.response_decision_index)
        if pair in pairs:
            raise ValueError("Duplicate commentary and response-decision pairs are invalid.")
        pairs.add(pair)

    canonical_links = tuple(
        sorted(
            retained_links,
            key=lambda item: (
                commentary_order[item.commentary_id],
                item.response_decision_index,
                item.link_id,
            ),
        )
    )
    return canonical_commentaries, canonical_links
