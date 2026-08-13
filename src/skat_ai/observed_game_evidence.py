from dataclasses import dataclass
from typing import Any

from skat_ai.observed_game_contracts import (
    ObservedGameRecordV1,
    _build_perspective_playable_hand,
    _reconcile_complete_cards,
)
from skat_ai.observed_game_trace import (
    ObservedGameTraceSummaryV1,
    _require_version,
    validate_observed_game_trace_v1,
)

OBSERVED_GAME_EVIDENCE_VERSION = 1
OBSERVED_GAME_EVIDENCE_POLICY = "derived_from_retained_observations"


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ObservedGameEvidenceSummaryV1:
    """Deterministic capabilities derived only from retained observed facts."""

    observed_game_evidence_version: int = OBSERVED_GAME_EVIDENCE_VERSION
    play_count: int
    completed_trick_count: int
    current_trick_play_count: int
    perspective_initial_hand_known: bool
    original_skat_known: bool
    discarded_cards_known: bool
    complete_play_trace: bool
    perspective_decision_samples_reconstructable: bool
    all_player_decision_samples_reconstructable: bool
    discard_review_reconstructable: bool
    complete_initial_deal_reconstructable: bool
    commentary_count: int
    response_link_count: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("ObservedGameEvidenceSummaryV1 must be constructed by its focused builder.")

    @classmethod
    def _from_validated(
        cls,
        *,
        play_count: int,
        completed_trick_count: int,
        current_trick_play_count: int,
        perspective_initial_hand_known: bool,
        original_skat_known: bool,
        discarded_cards_known: bool,
        complete_play_trace: bool,
        perspective_decision_samples_reconstructable: bool,
        all_player_decision_samples_reconstructable: bool,
        discard_review_reconstructable: bool,
        complete_initial_deal_reconstructable: bool,
        commentary_count: int,
        response_link_count: int,
    ) -> "ObservedGameEvidenceSummaryV1":
        value = object.__new__(cls)
        for field_name, field_value in (
            ("observed_game_evidence_version", OBSERVED_GAME_EVIDENCE_VERSION),
            ("play_count", play_count),
            ("completed_trick_count", completed_trick_count),
            ("current_trick_play_count", current_trick_play_count),
            ("perspective_initial_hand_known", perspective_initial_hand_known),
            ("original_skat_known", original_skat_known),
            ("discarded_cards_known", discarded_cards_known),
            ("complete_play_trace", complete_play_trace),
            (
                "perspective_decision_samples_reconstructable",
                perspective_decision_samples_reconstructable,
            ),
            (
                "all_player_decision_samples_reconstructable",
                all_player_decision_samples_reconstructable,
            ),
            ("discard_review_reconstructable", discard_review_reconstructable),
            (
                "complete_initial_deal_reconstructable",
                complete_initial_deal_reconstructable,
            ),
            ("commentary_count", commentary_count),
            ("response_link_count", response_link_count),
        ):
            object.__setattr__(value, field_name, field_value)
        value._validate_relationships()
        return value

    def _validate_relationships(self) -> None:
        _require_version(
            self.observed_game_evidence_version,
            OBSERVED_GAME_EVIDENCE_VERSION,
            "observed_game_evidence_version",
        )
        for field_name in (
            "play_count",
            "completed_trick_count",
            "current_trick_play_count",
            "commentary_count",
            "response_link_count",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        for field_name in (
            "perspective_initial_hand_known",
            "original_skat_known",
            "discarded_cards_known",
            "complete_play_trace",
            "perspective_decision_samples_reconstructable",
            "all_player_decision_samples_reconstructable",
            "discard_review_reconstructable",
            "complete_initial_deal_reconstructable",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be a boolean.")
        if self.current_trick_play_count > 2 or (
            self.completed_trick_count * 3 + self.current_trick_play_count != self.play_count
        ):
            raise ValueError("Trick counts must reconcile with play_count.")
        if self.all_player_decision_samples_reconstructable != self.complete_play_trace:
            raise ValueError(
                "all_player_decision_samples_reconstructable must equal complete_play_trace."
            )
        if self.complete_play_trace and (
            self.play_count != 30
            or self.completed_trick_count != 10
            or self.current_trick_play_count != 0
            or not self.perspective_decision_samples_reconstructable
        ):
            raise ValueError("Complete trace evidence relationships are inconsistent.")
        if self.discard_review_reconstructable and not (
            self.original_skat_known and self.discarded_cards_known
        ):
            raise ValueError("Discard review requires known original Skat and Discards.")
        if self.complete_initial_deal_reconstructable and not (
            self.complete_play_trace and self.original_skat_known and self.discarded_cards_known
        ):
            raise ValueError(
                "Complete initial Deal reconstruction requires complete Play, Skat, "
                "and Discard evidence."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_game_evidence_version": self.observed_game_evidence_version,
            "play_count": self.play_count,
            "completed_trick_count": self.completed_trick_count,
            "current_trick_play_count": self.current_trick_play_count,
            "perspective_initial_hand_known": self.perspective_initial_hand_known,
            "original_skat_known": self.original_skat_known,
            "discarded_cards_known": self.discarded_cards_known,
            "complete_play_trace": self.complete_play_trace,
            "perspective_decision_samples_reconstructable": (
                self.perspective_decision_samples_reconstructable
            ),
            "all_player_decision_samples_reconstructable": (
                self.all_player_decision_samples_reconstructable
            ),
            "discard_review_reconstructable": self.discard_review_reconstructable,
            "complete_initial_deal_reconstructable": (self.complete_initial_deal_reconstructable),
            "commentary_count": self.commentary_count,
            "response_link_count": self.response_link_count,
        }


def build_observed_game_evidence_summary_v1(
    record: ObservedGameRecordV1,
) -> ObservedGameEvidenceSummaryV1:
    """Builds evidence capabilities without constructing or executing a Request."""
    if not isinstance(record, ObservedGameRecordV1):
        raise ValueError("record must be ObservedGameRecordV1.")
    perspective_playable_hand = _build_perspective_playable_hand(
        perspective_player_id=record.perspective_player_id,
        perspective_initial_hand=record.perspective_initial_hand,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        original_skat=record.original_skat,
        discarded_cards=record.discarded_cards,
    )
    trace = validate_observed_game_trace_v1(
        plays=record.plays,
        seat_order_player_ids=tuple(player.player_id for player in record.players),
        perspective_player_id=record.perspective_player_id,
        perspective_initial_hand=record.perspective_initial_hand,
        perspective_playable_hand=perspective_playable_hand,
        declarer_player_id=record.declarer_player_id,
        declaration=record.declaration,
        original_skat=record.original_skat,
        discarded_cards=record.discarded_cards,
        game_timecode=record.game_timecode,
    )
    return build_observed_game_evidence_summary_from_trace_v1(record, trace)


def build_observed_game_evidence_summary_from_trace_v1(
    record: ObservedGameRecordV1,
    trace: ObservedGameTraceSummaryV1,
) -> ObservedGameEvidenceSummaryV1:
    """Builds evidence capabilities from one already validated retained trace."""
    if not isinstance(record, ObservedGameRecordV1):
        raise ValueError("record must be ObservedGameRecordV1.")
    if not isinstance(trace, ObservedGameTraceSummaryV1):
        raise ValueError("trace must be ObservedGameTraceSummaryV1.")
    if tuple(play.to_dict() for play in trace.plays) != tuple(
        play.to_dict() for play in record.plays
    ):
        raise ValueError("trace must describe the exact observed Game Plays.")
    complete_play_trace = trace.complete_play_trace
    if complete_play_trace:
        assert record.declarer_player_id is not None
        assert record.declaration is not None
        _reconcile_complete_cards(
            trace=trace,
            perspective_player_id=record.perspective_player_id,
            perspective_initial_hand=record.perspective_initial_hand,
            declarer_player_id=record.declarer_player_id,
            declaration=record.declaration,
            original_skat=record.original_skat,
            discarded_cards=record.discarded_cards,
        )
    play_count = len(trace.plays)

    perspective_hand_transformation_known = False
    if record.perspective_initial_hand is not None and record.declaration is not None:
        perspective_hand_transformation_known = (
            record.perspective_player_id != record.declarer_player_id
            or record.declaration.hand_game
            or (record.original_skat is not None and record.discarded_cards is not None)
        )
    perspective_samples = complete_play_trace or perspective_hand_transformation_known

    discard_review = False
    if (
        record.declaration is not None
        and not record.declaration.hand_game
        and record.original_skat is not None
        and record.discarded_cards is not None
    ):
        discard_review = complete_play_trace or (
            record.perspective_player_id == record.declarer_player_id
            and record.perspective_initial_hand is not None
        )

    discarded_cards_known = record.discarded_cards is not None
    complete_initial_deal = (
        complete_play_trace and record.original_skat is not None and discarded_cards_known
    )
    return ObservedGameEvidenceSummaryV1._from_validated(
        play_count=play_count,
        completed_trick_count=play_count // 3,
        current_trick_play_count=play_count % 3,
        perspective_initial_hand_known=record.perspective_initial_hand is not None,
        original_skat_known=record.original_skat is not None,
        discarded_cards_known=discarded_cards_known,
        complete_play_trace=complete_play_trace,
        perspective_decision_samples_reconstructable=perspective_samples,
        all_player_decision_samples_reconstructable=complete_play_trace,
        discard_review_reconstructable=discard_review,
        complete_initial_deal_reconstructable=complete_initial_deal,
        commentary_count=len(record.commentaries),
        response_link_count=len(record.response_links),
    )
