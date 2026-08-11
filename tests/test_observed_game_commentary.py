from dataclasses import FrozenInstanceError, fields

import pytest
from test_historical_game import build_historical_input
from test_observed_game_contracts import (
    build_observed_record,
    declaration_from_historical,
    observed_plays_from_historical,
)

from skat_ai.match_source_metadata import MediaTimecodeV1
from skat_ai.observed_game_commentary import (
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)


def commentary(
    commentary_id: str,
    decision_index: int,
    subject_player_id: str,
    *,
    commentator_player_id: str | None = "player-a",
    commentator_name: str | None = None,
    text: str = "Observed explanation.",
    start_ms: int | None = None,
) -> ObservedDecisionCommentaryV1:
    return ObservedDecisionCommentaryV1(
        commentary_id=commentary_id,
        decision_index=decision_index,
        subject_player_id=subject_player_id,
        commentator_player_id=commentator_player_id,
        commentator_name=commentator_name,
        text=text,
        commentary_timecode=(
            None
            if start_ms is None
            else MediaTimecodeV1(start_offset_ms=start_ms, end_offset_ms=None)
        ),
    )


def link(
    link_id: str,
    commentary_id: str,
    response_decision_index: int,
) -> ObservedDecisionResponseLinkV1:
    return ObservedDecisionResponseLinkV1(
        link_id=link_id,
        commentary_id=commentary_id,
        response_decision_index=response_decision_index,
    )


def _partial_values() -> tuple[dict, tuple]:
    data = build_historical_input()
    return data, observed_plays_from_historical(data, count=6)


def test_free_text_commentary_targets_all_three_players_and_preserves_multiline_text() -> None:
    data, plays = _partial_values()
    items = tuple(
        commentary(
            f"comment-{index}",
            index,
            play.player_id,
            text=("First line\nSecond line" if index == 2 else f"Comment {index}."),
        )
        for index, play in enumerate(plays[:3], start=1)
    )
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=items,
    )
    assert {item.subject_player_id for item in record.commentaries} == {
        "player-a",
        "player-b",
        "player-c",
    }
    assert record.commentaries[1].text == "First line\nSecond line"
    assert {
        "tactical_category",
        "sentiment",
        "error_type",
        "suit_signal",
        "requested_action",
        "strategic_value",
        "optimality",
    }.isdisjoint(record.commentaries[0].to_dict())


def test_match_player_external_and_combined_commentator_identities_are_supported() -> None:
    data, plays = _partial_values()
    items = (
        commentary("match-player", 1, plays[0].player_id),
        commentary(
            "external",
            2,
            plays[1].player_id,
            commentator_player_id=None,
            commentator_name="Video analyst",
        ),
        commentary(
            "combined",
            3,
            plays[2].player_id,
            commentator_player_id="player-c",
            commentator_name="Carol on the broadcast",
        ),
    )
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=items,
    )
    assert record.commentaries[0].commentator_player_id == "player-a"
    assert record.commentaries[1].commentator_name == "Video analyst"
    assert record.commentaries[2].commentator_player_id == "player-c"
    assert record.commentaries[2].commentator_name == "Carol on the broadcast"


def test_commentary_rejects_missing_identity_empty_or_padded_text() -> None:
    with pytest.raises(ValueError, match="commentator identity"):
        commentary(
            "missing",
            1,
            "player-a",
            commentator_player_id=None,
            commentator_name=None,
        )
    for text in ("", " padded", "padded "):
        with pytest.raises(ValueError, match="text"):
            commentary("bad-text", 1, "player-a", text=text)


def test_commentary_references_subject_commentator_and_timecode_exactly() -> None:
    data, plays = _partial_values()
    base = {
        "declarer_player_id": data["declarer_player_id"],
        "declaration": declaration_from_historical(data),
        "plays": plays,
    }
    invalid_items = (
        (commentary("missing-play", 7, "player-a"), "retained Play"),
        (commentary("wrong-subject", 1, "player-b"), "subject_player_id"),
        (
            commentary(
                "foreign-commentator",
                1,
                plays[0].player_id,
                commentator_player_id="foreign",
            ),
            "unknown commentator",
        ),
        (
            commentary("outside", 1, plays[0].player_id, start_ms=19_999),
            "within game_timecode",
        ),
    )
    for item, message in invalid_items:
        with pytest.raises(ValueError, match=message):
            build_observed_record(commentaries=(item,), **base)


def test_commentary_ids_are_unique_and_multiple_items_may_share_one_decision() -> None:
    data, plays = _partial_values()
    shared = (
        commentary("comment-a", 1, plays[0].player_id),
        commentary("comment-b", 1, plays[0].player_id),
    )
    assert len(
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            plays=plays,
            commentaries=shared,
        ).commentaries
    ) == 2
    with pytest.raises(ValueError, match="commentary_id"):
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            plays=plays,
            commentaries=(shared[0], shared[0]),
        )


def test_response_links_support_multiple_later_decisions_by_any_player() -> None:
    data, plays = _partial_values()
    item = commentary("comment-1", 1, plays[0].player_id)
    links = (
        link("link-2", "comment-1", 3),
        link("link-1", "comment-1", 2),
        link("link-3", "comment-1", 6),
    )
    record = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=(item,),
        response_links=links,
    )
    assert [item.response_decision_index for item in record.response_links] == [2, 3, 6]
    assert {plays[item.response_decision_index - 1].player_id for item in links} == {
        "player-a",
        "player-b",
        "player-c",
    }
    assert {
        "response_player_id",
        "causality",
        "correct_response",
        "tactical_category",
        "strategic_value",
    }.isdisjoint(record.response_links[0].to_dict())


@pytest.mark.parametrize(
    ("links", "message"),
    (
        ((link("link-1", "missing", 2),), "retained commentary"),
        ((link("link-1", "comment-1", 7),), "retained response Play"),
        ((link("link-1", "comment-1", 1),), "later observed decision"),
        ((link("link-1", "comment-1", 2), link("link-1", "comment-1", 3)), "link_id"),
        (
            (link("link-1", "comment-1", 2), link("link-2", "comment-1", 2)),
            "Duplicate commentary",
        ),
    ),
)
def test_response_links_reject_invalid_references_direction_and_duplicates(
    links,
    message: str,
) -> None:
    data, plays = _partial_values()
    with pytest.raises(ValueError, match=message):
        build_observed_record(
            declarer_player_id=data["declarer_player_id"],
            declaration=declaration_from_historical(data),
            plays=plays,
            commentaries=(commentary("comment-1", 1, plays[0].player_id),),
            response_links=links,
        )


def test_annotation_order_is_canonical_and_independent_from_caller_order() -> None:
    data, plays = _partial_values()
    commentaries = (
        commentary("untimed", 2, plays[1].player_id),
        commentary("late", 1, plays[0].player_id, start_ms=40_000),
        commentary("early-z", 1, plays[0].player_id, start_ms=30_000),
        commentary("early-a", 1, plays[0].player_id, start_ms=30_000),
    )
    links = (
        link("z-link", "untimed", 6),
        link("late-link", "late", 5),
        link("early-link", "early-a", 3),
    )
    first = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=commentaries,
        response_links=links,
    )
    second = build_observed_record(
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        plays=plays,
        commentaries=tuple(reversed(commentaries)),
        response_links=tuple(reversed(links)),
    )
    assert [item.commentary_id for item in first.commentaries] == [
        "early-a",
        "early-z",
        "late",
        "untimed",
    ]
    assert [item.link_id for item in first.response_links] == [
        "early-link",
        "late-link",
        "z-link",
    ]
    assert first.to_dict() == second.to_dict()


def test_commentary_and_link_values_are_frozen_slotted_keyword_only() -> None:
    item = commentary("comment-1", 1, "player-a")
    response = link("link-1", "comment-1", 2)
    assert [field.name for field in fields(item)] == [
        "decision_commentary_version",
        "commentary_id",
        "decision_index",
        "subject_player_id",
        "commentator_player_id",
        "commentator_name",
        "text",
        "commentary_timecode",
    ]
    assert [field.name for field in fields(response)] == [
        "decision_response_link_version",
        "link_id",
        "commentary_id",
        "response_decision_index",
    ]
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.text = "Changed"
    with pytest.raises(TypeError):
        ObservedDecisionResponseLinkV1("link", "comment", 2)
