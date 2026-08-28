import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from test_historical_game import build_historical_input
from test_match_capture_contracts import _capture, _participants

import skatmind
import skatmind.api.v1 as api_v1
import skatmind.api.v1.session as session_api
from scripts.validate_generated_outputs_schema import SCENARIOS
from skatmind.game_declaration import GameDeclaration
from skatmind.historical_game import HISTORICAL_SEATS
from skatmind.match_capture_contracts import MATCH_CAPTURE_CONTRACT_VERSION
from skatmind.match_source_metadata import MediaTimecodeV1
from skatmind.observed_game_commentary import (
    DECISION_COMMENTARY_POLICY,
    DECISION_COMMENTARY_VERSION,
    DECISION_RESPONSE_LINK_POLICY,
    DECISION_RESPONSE_LINK_VERSION,
    ObservedDecisionCommentaryV1,
    ObservedDecisionResponseLinkV1,
)
from skatmind.observed_game_contracts import (
    OBSERVED_GAME_CONTRACT_VERSION,
    OBSERVED_GAME_FACT_POLICY,
    ObservedGamePlayerV1,
    ObservedGameRecordV1,
    build_observed_game_record_v1,
)
from skatmind.observed_game_evidence import (
    OBSERVED_GAME_EVIDENCE_POLICY,
    OBSERVED_GAME_EVIDENCE_VERSION,
)
from skatmind.observed_game_trace import (
    OBSERVED_GAME_TRACE_POLICY,
    OBSERVED_PLAY_VERSION,
    ObservedPlayV1,
)
from skatmind.session_contracts import SESSION_CONTRACT_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEAT_ORDER_PLAYER_IDS = ("player-a", "player-b", "player-c")


def build_observed_match(*, perspective_player_id: str = "player-a"):
    return _capture(
        participants=_participants(snapshots=False),
        perspective_player_id=perspective_player_id,
    )


def declaration_from_historical(data: dict) -> GameDeclaration:
    declaration = data["declaration"]
    return GameDeclaration(
        game_type=declaration["game_type"],
        hand_game=declaration.get("hand_game", False),
        ouvert=declaration.get("ouvert", False),
        schneider_announced=declaration.get("schneider_announced", False),
        schwarz_announced=declaration.get("schwarz_announced", False),
        matadors=declaration.get("matadors"),
        bid_value=declaration.get("bid_value"),
    )


def observed_plays_from_historical(
    data: dict,
    *,
    count: int = 30,
) -> tuple[ObservedPlayV1, ...]:
    flat_plays = [play for trick in data["tricks"] for play in trick["plays"]]
    return tuple(
        ObservedPlayV1(
            decision_index=index,
            player_id=play["player_id"],
            card=play["card"],
            decision_timecode=None,
        )
        for index, play in enumerate(flat_plays[:count], start=1)
    )


def build_observed_record(**overrides) -> ObservedGameRecordV1:
    values = {
        "game_id": "observed-game-1",
        "match_position": 1,
        "game_timecode": MediaTimecodeV1(
            start_offset_ms=20_000,
            end_offset_ms=120_000,
        ),
        "seat_order_player_ids": SEAT_ORDER_PLAYER_IDS,
        "perspective_initial_hand": None,
        "declarer_player_id": None,
        "declaration": None,
        "original_skat": None,
        "discarded_cards": None,
        "plays": (),
        "commentaries": (),
        "response_links": (),
    }
    match_definition = overrides.pop("match_definition", build_observed_match())
    values.update(overrides)
    return build_observed_game_record_v1(match_definition, **values)


def build_complete_observed_record(
    *,
    game_type: str = "grand",
    hand_game: bool = False,
    perspective_player_id: str = "player-a",
    include_initial_hand: bool = True,
    include_original_skat: bool = True,
    include_discards: bool = True,
) -> ObservedGameRecordV1:
    data = build_historical_input(game_type=game_type, hand_game=hand_game)
    initial_hand = next(
        player["initial_hand"]
        for player in data["players"]
        if player["player_id"] == perspective_player_id
    )
    return build_observed_record(
        match_definition=build_observed_match(
            perspective_player_id=perspective_player_id
        ),
        game_id=f"observed-{game_type}-game",
        perspective_initial_hand=initial_hand if include_initial_hand else None,
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"] if include_original_skat else None,
        discarded_cards=data["discarded_cards"] if include_discards else None,
        plays=observed_plays_from_historical(data),
    )


def test_versions_policies_and_existing_versions_are_exact() -> None:
    assert (
        OBSERVED_GAME_CONTRACT_VERSION,
        OBSERVED_PLAY_VERSION,
        OBSERVED_GAME_EVIDENCE_VERSION,
        DECISION_COMMENTARY_VERSION,
        DECISION_RESPONSE_LINK_VERSION,
    ) == (1, 1, 1, 1, 1)
    assert OBSERVED_GAME_FACT_POLICY == "caller_observed_without_hidden_completion"
    assert OBSERVED_GAME_TRACE_POLICY == "chronological_public_play_trace"
    assert OBSERVED_GAME_EVIDENCE_POLICY == "derived_from_retained_observations"
    assert DECISION_COMMENTARY_POLICY == "free_text_without_required_taxonomy"
    assert DECISION_RESPONSE_LINK_POLICY == "later_observed_decision_reference"
    assert MATCH_CAPTURE_CONTRACT_VERSION == 1
    assert SESSION_CONTRACT_VERSION == 1


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_new_leaf_contracts_reject_wrong_versions(version) -> None:
    with pytest.raises(ValueError, match="observed_play_version"):
        ObservedPlayV1(
            observed_play_version=version,
            decision_index=1,
            player_id="player-a",
            card="CA",
            decision_timecode=None,
        )
    with pytest.raises(ValueError, match="decision_commentary_version"):
        ObservedDecisionCommentaryV1(
            decision_commentary_version=version,
            commentary_id="comment-1",
            decision_index=1,
            subject_player_id="player-a",
            commentator_player_id="player-a",
            commentator_name=None,
            text="Comment.",
            commentary_timecode=None,
        )
    with pytest.raises(ValueError, match="decision_response_link_version"):
        ObservedDecisionResponseLinkV1(
            decision_response_link_version=version,
            link_id="link-1",
            commentary_id="comment-1",
            response_decision_index=2,
        )


def test_game_players_are_exact_match_players_in_canonical_historical_seats() -> None:
    record = build_observed_record(
        seat_order_player_ids=("player-c", "player-a", "player-b")
    )
    assert tuple(player.player_id for player in record.players) == (
        "player-c",
        "player-a",
        "player-b",
    )
    assert tuple(player.seat for player in record.players) == HISTORICAL_SEATS
    assert record.perspective_player_id == "player-a"
    assert record.match_id == "match-160"
    assert record.players[0].to_dict() == {
        "player_id": "player-c",
        "seat": "forehand",
    }
    assert {"player_label", "platform_player_id", "statistics_snapshot"}.isdisjoint(
        record.players[0].to_dict()
    )


@pytest.mark.parametrize(
    ("seat_order", "message"),
    (
        (("player-a", "player-b"), "exactly three"),
        (("player-a", "player-a", "player-c"), "unique"),
        (("player-a", "player-b", "foreign"), "exactly the Match"),
        (("player-a", "player-b", "me"), "non-relative"),
    ),
)
def test_game_player_linkage_rejects_missing_duplicate_foreign_or_relative_ids(
    seat_order,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_observed_record(seat_order_player_ids=seat_order)


@pytest.mark.parametrize("position", (1, 36))
def test_match_position_accepts_exact_format_bounds(position: int) -> None:
    assert build_observed_record(match_position=position).match_position == position


@pytest.mark.parametrize("position", (0, 37, True, 1.0))
def test_match_position_rejects_out_of_range_or_non_strict_values(position) -> None:
    with pytest.raises(ValueError, match="match_position"):
        build_observed_record(match_position=position)


def test_game_timecode_must_be_inside_match_bounds() -> None:
    assert build_observed_record(
        game_timecode=MediaTimecodeV1(
            start_offset_ms=12_345,
            end_offset_ms=7_654_321,
        )
    ).game_timecode is not None
    for timecode in (
        MediaTimecodeV1(start_offset_ms=12_344, end_offset_ms=20_000),
        MediaTimecodeV1(start_offset_ms=20_000, end_offset_ms=7_654_322),
        MediaTimecodeV1(start_offset_ms=7_654_322, end_offset_ms=None),
    ):
        with pytest.raises(ValueError, match="within"):
            build_observed_record(game_timecode=timecode)


def test_optional_perspective_hand_and_original_skat_are_canonical_and_disjoint() -> None:
    record = build_observed_record(
        perspective_initial_hand=(
            "S10",
            "CA",
            "C10",
            "CK",
            "CQ",
            "CJ",
            "C9",
            "C8",
            "C7",
            "SA",
        ),
        original_skat=("D7", "H7"),
    )
    assert record.perspective_initial_hand == (
        "CA",
        "C10",
        "CK",
        "CQ",
        "CJ",
        "C9",
        "C8",
        "C7",
        "SA",
        "S10",
    )
    assert record.original_skat == ("H7", "D7")
    assert build_observed_record().perspective_initial_hand is None
    assert build_observed_record().original_skat is None

    with pytest.raises(ValueError, match="disjoint"):
        build_observed_record(
            perspective_initial_hand=tuple(build_historical_input()["players"][0]["initial_hand"]),
            original_skat=("CA", "D7"),
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("perspective_initial_hand", ("CA",), "Card counts"),
        ("perspective_initial_hand", ("CA",) * 10, "duplicate"),
        (
            "perspective_initial_hand",
            ("XX", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10"),
            "invalid",
        ),
        ("original_skat", ("CA",), "Card counts"),
        ("original_skat", ("CA", "CA"), "duplicate"),
    ),
)
def test_optional_card_evidence_rejects_bad_cardinality_identity_or_uniqueness(
    field_name: str,
    value,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_observed_record(**{field_name: value})


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    (
        ("clubs", False, False),
        ("spades", False, False),
        ("hearts", False, False),
        ("diamonds", False, False),
        ("grand", True, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ),
)
def test_existing_declaration_variants_are_retained(
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    declaration = GameDeclaration(
        game_type=game_type,
        hand_game=hand_game,
        ouvert=ouvert,
        matadors=None if game_type == "null" else 1,
        bid_value=18,
    )
    record = build_observed_record(
        declarer_player_id="player-b",
        declaration=declaration,
        discarded_cards=() if declaration.hand_game else ("D8", "D7"),
    )
    assert record.declaration == declaration
    assert record.declarer_player_id == "player-b"


def test_declarer_declaration_and_play_relationships_are_exact() -> None:
    with pytest.raises(ValueError, match="both null or both present"):
        build_observed_record(declarer_player_id="player-b")
    with pytest.raises(ValueError, match="both null or both present"):
        build_observed_record(declaration=GameDeclaration(game_type="grand"))
    with pytest.raises(ValueError, match="exact Game Player"):
        build_observed_record(
            declarer_player_id="foreign",
            declaration=GameDeclaration(game_type="grand"),
        )


@pytest.mark.parametrize(
    ("values", "message"),
    (
        ({"decision_index": 0}, "positive integer"),
        ({"decision_index": True}, "positive integer"),
        ({"player_id": "me"}, "non-relative"),
        ({"card": "XX"}, "valid Skat Card"),
        ({"decision_timecode": "00:10"}, "MediaTimecodeV1"),
    ),
)
def test_observed_play_rejects_invalid_index_identity_card_or_timecode(
    values: dict[str, object],
    message: str,
) -> None:
    play_values = {
        "decision_index": 1,
        "player_id": "player-a",
        "card": "CA",
        "decision_timecode": None,
    }
    play_values.update(values)
    with pytest.raises(ValueError, match=message):
        ObservedPlayV1(**play_values)
    with pytest.raises(ValueError, match="require both Declarer"):
        build_observed_record(
            plays=(
                ObservedPlayV1(
                    decision_index=1,
                    player_id="player-a",
                    card="CA",
                    decision_timecode=None,
                ),
            )
        )


def test_discards_preserve_unknown_known_empty_and_exact_two_card_semantics() -> None:
    hand = build_observed_record(
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand", hand_game=True),
        discarded_cards=(),
    )
    non_hand = build_observed_record(
        declarer_player_id="player-b",
        declaration=GameDeclaration(game_type="grand"),
        discarded_cards=("D7", "CA"),
    )
    assert build_observed_record().discarded_cards is None
    assert hand.discarded_cards == ()
    assert non_hand.discarded_cards == ("CA", "D7")
    with pytest.raises(ValueError, match="Hand games"):
        build_observed_record(
            declarer_player_id="player-b",
            declaration=GameDeclaration(game_type="grand", hand_game=True),
            discarded_cards=("D8", "D7"),
        )
    with pytest.raises(ValueError, match="non-Hand"):
        build_observed_record(
            declarer_player_id="player-b",
            declaration=GameDeclaration(game_type="grand"),
            discarded_cards=(),
        )
    with pytest.raises(ValueError, match="Card counts"):
        build_observed_record(discarded_cards=("D7",))


def test_record_values_are_frozen_slotted_keyword_only_with_exact_fields() -> None:
    record = build_observed_record()
    player = record.players[0]
    play = ObservedPlayV1(
        decision_index=1,
        player_id="player-a",
        card="CA",
        decision_timecode=None,
    )
    assert [field.name for field in fields(record)] == [
        "observed_game_contract_version",
        "game_id",
        "match_id",
        "match_position",
        "game_timecode",
        "players",
        "perspective_player_id",
        "perspective_initial_hand",
        "declarer_player_id",
        "declaration",
        "original_skat",
        "discarded_cards",
        "plays",
        "commentaries",
        "response_links",
    ]
    for value in (record, player, play):
        assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        record.game_id = "changed"
    with pytest.raises(TypeError, match="focused builder"):
        ObservedGameRecordV1()
    with pytest.raises(TypeError):
        ObservedGamePlayerV1("player-a", "forehand")


def test_record_serialization_is_deterministic_defensive_and_observation_only() -> None:
    hand = list(build_historical_input()["players"][0]["initial_hand"])
    timecode = MediaTimecodeV1(start_offset_ms=20_000, end_offset_ms=120_000)
    record = build_observed_record(
        game_timecode=timecode,
        perspective_initial_hand=hand,
    )
    hand.clear()
    object.__setattr__(timecode, "start_offset_ms", 99)

    first = record.to_dict()
    second = record.to_dict()
    first["players"][0]["player_id"] = "changed"
    first["perspective_initial_hand"][0] = "D7"
    assert second["players"][0]["player_id"] == "player-a"
    assert second["perspective_initial_hand"][0] == "CA"
    assert second["game_timecode"]["start_offset_ms"] == 20_000
    assert list(second) == [field.name for field in fields(record)]
    forbidden = {
        "title",
        "source_url",
        "source_channel_name",
        "statistics_snapshot",
        "result",
        "settlement",
        "path",
        "created_at",
        "tactical_category",
    }
    assert forbidden.isdisjoint(second)
    json.dumps(second)


def test_complete_fixture_helper_reuses_existing_suit_grand_and_null_deals() -> None:
    for game_type, hand_game in (("clubs", True), ("grand", False), ("null", False)):
        record = build_complete_observed_record(
            game_type=game_type,
            hand_game=hand_game,
        )
        assert len(record.plays) == 30
        assert record.declaration.game_type == game_type


def test_public_package_schema_and_generated_output_boundaries_are_unchanged() -> None:
    assert skatmind.__all__ == ("api", "errors", "__version__")
    for name in (
        "ObservedGameRecordV1",
        "ObservedPlayV1",
        "ObservedDecisionCommentaryV1",
        "ObservedGameEvidenceSummaryV1",
    ):
        assert name not in api_v1.__all__
        assert name not in session_api.__all__
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 71
    assert len(
        tuple(
            (PROJECT_ROOT / "src" / "skatmind" / "schema_resources").glob(
                "*.schema.json"
            )
        )
    ) == 71
    assert len(SCENARIOS) == 98
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == "0.17.0"
    assert skatmind.__version__ == "0.17.0"
