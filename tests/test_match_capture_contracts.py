import json
import socket
import tomllib
import urllib.request
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from test_fixed_three_player_historical_list import build_list_input
from test_opponent_statistics import (
    build_historical_source,
    build_valid_record,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.api.v1.session as session_api
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.fixed_three_player_historical_list import (
    build_fixed_three_player_historical_list,
)
from skat_ai.fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
)
from skat_ai.match_capture_contracts import (
    MATCH_CAPTURE_CONTRACT_VERSION,
    MATCH_PERSPECTIVE_POLICY,
    MatchCaptureDefinitionV1,
)
from skat_ai.match_player_snapshot import (
    MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION,
    MatchParticipantV1,
    MatchPlayerStatisticsSnapshotV1,
)
from skat_ai.match_source_metadata import (
    MATCH_SOURCE_KINDS,
    MATCH_SOURCE_METADATA_VERSION,
    MEDIA_TIMECODE_VERSION,
    MatchSourceMetadataV1,
    MediaTimecodeV1,
)
from skat_ai.match_tournament_format import (
    EUROSKAT_36_STANDARD_V1_FORMAT,
    MATCH_TOURNAMENT_FORMAT_REGISTRY,
    MATCH_TOURNAMENT_FORMAT_REGISTRY_POLICY,
    MATCH_TOURNAMENT_FORMAT_VERSION,
    SUPPORTED_MATCH_TOURNAMENT_FORMAT_IDS,
    MatchTournamentFormatV1,
    get_match_tournament_format_v1,
)
from skat_ai.opponent_statistics import (
    OpponentStatisticsInput,
    build_opponent_statistics_input,
    build_serializable_opponent_statistics_input,
)
from skat_ai.session_contracts import SESSION_CONTRACT_VERSION, SessionPlayerV1

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _statistics_record(
    player_id: str = "player-a",
    source_type: str = "online_platform",
):
    record = build_valid_record()
    record["player_id"] = player_id
    record.pop("player_label", None)
    if source_type == "manual_entry":
        record["source"] = {
            "source_type": "manual_entry",
            "source_name": "Observed profile",
            "captured_at": "2026-08-10T10:00:00Z",
        }
    elif source_type == "historical_games":
        record["source"] = build_historical_source()
        record["source"]["source_player_id"] = player_id
    return build_opponent_statistics_input(
        {"schema_version": 1, "records": [record]}
    ).records[0]


def _snapshot(
    player_id: str = "player-a",
    snapshot_id: str = "snapshot-a",
    source_type: str = "online_platform",
) -> MatchPlayerStatisticsSnapshotV1:
    record = _statistics_record(player_id, source_type)
    observed_at = {
        "online_platform": "2026-07-23T10:00:00Z",
        "manual_entry": "2026-08-10T12:00:00+02:00",
        "historical_games": "2026-07-20T19:00:00+02:00",
    }[source_type]
    return MatchPlayerStatisticsSnapshotV1(
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        statistics_record=record,
    )


def _participants(*, snapshots: bool = True) -> tuple[MatchParticipantV1, ...]:
    return tuple(
        MatchParticipantV1(
            player_id=player_id,
            player_label=label,
            platform_player_id=platform_id,
            table_place=table_place,
            statistics_snapshot=(
                _snapshot(player_id, f"snapshot-{index}")
                if snapshots and index == 1
                else None
            ),
        )
        for index, (player_id, label, platform_id, table_place) in enumerate(
            (
                ("player-a", "Alice", "platform-a", "place_1"),
                ("player-b", None, "platform-b", "place_2"),
                ("player-c", "Carol", None, "place_3"),
            ),
            start=1,
        )
    )


def _youtube_source() -> MatchSourceMetadataV1:
    return MatchSourceMetadataV1(
        source_kind="youtube_video",
        source_url="https://www.youtube.com/watch?v=AbC_123-xy",
        source_title="EuroSkat 36er Standard Match",
        source_channel_name="Example Channel",
        match_timecode=MediaTimecodeV1(
            start_offset_ms=12_345,
            end_offset_ms=7_654_321,
        ),
    )


def _capture(**overrides) -> MatchCaptureDefinitionV1:
    values = {
        "match_id": "match-160",
        "title": "Observed EuroSkat Match",
        "game_platform": "EuroSkat",
        "external_match_id": "external-match-42",
        "played_at": "2026-08-09T18:00:00Z",
        "tournament_format": get_match_tournament_format_v1(
            "euroskat_36_standard_v1"
        ),
        "source": _youtube_source(),
        "participants": _participants(),
        "perspective_player_id": "player-a",
    }
    values.update(overrides)
    return MatchCaptureDefinitionV1(**values)


def test_versions_policies_and_canonical_orders_are_exact() -> None:
    assert MATCH_CAPTURE_CONTRACT_VERSION == 1
    assert MATCH_SOURCE_METADATA_VERSION == 1
    assert MEDIA_TIMECODE_VERSION == 1
    assert MATCH_TOURNAMENT_FORMAT_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION == 1
    assert MATCH_SOURCE_KINDS == (
        "youtube_video",
        "other_video",
        "manual_observation",
    )
    assert SUPPORTED_MATCH_TOURNAMENT_FORMAT_IDS == (
        "euroskat_36_standard_v1",
    )
    assert MATCH_TOURNAMENT_FORMAT_REGISTRY_POLICY == (
        "append_only_named_format_definitions"
    )
    assert MATCH_PERSPECTIVE_POLICY == "one_declared_match_player"
    assert SESSION_CONTRACT_VERSION == 1


@pytest.mark.parametrize("version", (2, True, 1.0))
def test_every_new_contract_rejects_wrong_version(version) -> None:
    constructors = (
        lambda: MediaTimecodeV1(
            media_timecode_version=version,
            start_offset_ms=0,
            end_offset_ms=None,
        ),
        lambda: MatchSourceMetadataV1(
            match_source_metadata_version=version,
            source_kind="manual_observation",
            source_url=None,
            source_title="Manual observation",
            source_channel_name=None,
            match_timecode=None,
        ),
        lambda: MatchTournamentFormatV1(
            match_tournament_format_version=version,
            format_id="future_v1",
            provider="Provider",
            display_name="Future",
            player_count=3,
            game_count=36,
        ),
        lambda: MatchPlayerStatisticsSnapshotV1(
            match_player_statistics_snapshot_version=version,
            snapshot_id="snapshot-a",
            observed_at="2026-07-23T10:00:00Z",
            statistics_record=_statistics_record(),
        ),
        lambda: _capture(match_capture_contract_version=version),
    )
    for constructor in constructors:
        with pytest.raises(ValueError):
            constructor()


@pytest.mark.parametrize(
    ("start", "end"),
    ((0, None), (1, None), (0, 0), (1_000, 1_000), (1_000, 2_000)),
)
def test_media_timecode_accepts_strict_ordered_millisecond_bounds(
    start: int,
    end: int | None,
) -> None:
    value = MediaTimecodeV1(start_offset_ms=start, end_offset_ms=end)
    assert value.to_dict() == {
        "media_timecode_version": 1,
        "start_offset_ms": start,
        "end_offset_ms": end,
    }


@pytest.mark.parametrize(
    ("start", "end", "message"),
    (
        (-1, None, "start_offset_ms"),
        (True, None, "start_offset_ms"),
        (0, -1, "end_offset_ms"),
        (0, False, "end_offset_ms"),
        (2, 1, "must not precede"),
    ),
)
def test_media_timecode_rejects_invalid_bounds(start, end, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        MediaTimecodeV1(start_offset_ms=start, end_offset_ms=end)


def test_media_timecode_is_frozen_slotted_keyword_only_and_deterministic() -> None:
    value = MediaTimecodeV1(start_offset_ms=1, end_offset_ms=2)
    first = value.to_dict()
    second = value.to_dict()
    first["start_offset_ms"] = 99
    assert second["start_offset_ms"] == 1
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.end_offset_ms = 3
    with pytest.raises(TypeError):
        MediaTimecodeV1(1, 2)


@pytest.mark.parametrize(
    ("source_kind", "source_url", "channel"),
    (
        ("youtube_video", "https://youtu.be/abc?t=10", None),
        ("other_video", "https://media.example.test/video/1", "Media Archive"),
        ("manual_observation", None, None),
    ),
)
def test_all_source_kinds_have_exact_field_relationships(
    source_kind: str,
    source_url: str | None,
    channel: str | None,
) -> None:
    source = MatchSourceMetadataV1(
        source_kind=source_kind,
        source_url=source_url,
        source_title="Observed Match",
        source_channel_name=channel,
        match_timecode=None,
    )
    assert source.to_dict() == {
        "match_source_metadata_version": 1,
        "source_kind": source_kind,
        "source_url": source_url,
        "source_title": "Observed Match",
        "source_channel_name": channel,
        "match_timecode": None,
    }


@pytest.mark.parametrize(
    ("values", "message"),
    (
        ({"source_kind": "youtube_video", "source_url": None}, "required"),
        ({"source_kind": "other_video", "source_url": None}, "required"),
        ({"source_kind": "manual_observation", "source_url": "https://x.test"}, "null"),
        ({"source_kind": "manual_observation", "source_channel_name": "Channel"}, "null"),
        ({"source_kind": "future_source"}, "source_kind"),
        ({"source_title": None}, "non-empty string"),
        ({"source_title": " padded"}, "leading or trailing"),
        ({"source_channel_name": "padded "}, "leading or trailing"),
        ({"source_url": "not-a-url"}, "absolute HTTP"),
    ),
)
def test_source_metadata_rejects_invalid_relationships_and_strings(
    values: dict[str, object],
    message: str,
) -> None:
    source_values = {
        "source_kind": "youtube_video",
        "source_url": "https://youtube.example.test/video",
        "source_title": "Observed Match",
        "source_channel_name": None,
        "match_timecode": None,
    }
    source_values.update(values)
    with pytest.raises(ValueError, match=message):
        MatchSourceMetadataV1(**source_values)


def test_source_url_is_preserved_exactly_without_network_access(monkeypatch) -> None:
    def unexpected_network(*_args, **_kwargs):
        raise AssertionError("Source construction attempted network access.")

    monkeypatch.setattr(socket, "create_connection", unexpected_network)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected_network)
    url = "HTTPS://YouTube.Example/Watch?Video=CaseSensitive#At=10"
    source = MatchSourceMetadataV1(
        source_kind="youtube_video",
        source_url=url,
        source_title="Observed Match",
        source_channel_name=None,
        match_timecode=MediaTimecodeV1(start_offset_ms=0, end_offset_ms=None),
    )
    assert source.source_url == url
    assert source.to_dict()["source_url"] == url


def test_tournament_format_registry_is_exact_immutable_and_deterministic() -> None:
    format_definition = get_match_tournament_format_v1(
        "euroskat_36_standard_v1"
    )
    assert format_definition is EUROSKAT_36_STANDARD_V1_FORMAT
    assert tuple(MATCH_TOURNAMENT_FORMAT_REGISTRY) == (
        "euroskat_36_standard_v1",
    )
    assert MATCH_TOURNAMENT_FORMAT_REGISTRY[format_definition.format_id] is (
        format_definition
    )
    assert format_definition.to_dict() == {
        "match_tournament_format_version": 1,
        "format_id": "euroskat_36_standard_v1",
        "provider": "EuroSkat",
        "display_name": "36er Standard",
        "player_count": 3,
        "game_count": 36,
    }
    assert {
        "ranking",
        "qualification",
        "prize",
        "fee",
        "bonus_program",
    }.isdisjoint(format_definition.to_dict())
    with pytest.raises(TypeError):
        MATCH_TOURNAMENT_FORMAT_REGISTRY["future"] = format_definition
    with pytest.raises(FrozenInstanceError):
        format_definition.game_count = 18
    with pytest.raises(ValueError, match="Unknown Match tournament format"):
        get_match_tournament_format_v1("euroskat_36_zocker_v1")


@pytest.mark.parametrize(("field_name", "value"), (("player_count", True), ("game_count", 0)))
def test_tournament_format_rejects_invalid_counts(field_name: str, value) -> None:
    values = {
        "format_id": "future_v1",
        "provider": "Provider",
        "display_name": "Future Format",
        "player_count": 3,
        "game_count": 36,
    }
    values[field_name] = value
    with pytest.raises(ValueError, match=field_name):
        MatchTournamentFormatV1(**values)


@pytest.mark.parametrize(
    "source_type",
    ("online_platform", "manual_entry", "historical_games"),
)
def test_snapshot_reuses_all_existing_statistics_source_kinds(source_type: str) -> None:
    snapshot = _snapshot(source_type=source_type)
    serialized = snapshot.to_dict()
    assert serialized["statistics_record"]["source"]["source_type"] == source_type
    assert "normalized_profile_statistics" not in serialized["statistics_record"]
    assert "profile_derivation" not in serialized["statistics_record"]


def test_snapshot_requires_same_observation_instant_and_valid_identity() -> None:
    record = _statistics_record()
    snapshot = MatchPlayerStatisticsSnapshotV1(
        snapshot_id="snapshot-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=record,
    )
    assert snapshot.observed_at != snapshot.statistics_record.source.captured_at
    with pytest.raises(ValueError, match="same instant"):
        MatchPlayerStatisticsSnapshotV1(
            snapshot_id="snapshot-a",
            observed_at="2026-07-23T10:00:01Z",
            statistics_record=record,
        )
    with pytest.raises(ValueError, match="leading or trailing"):
        MatchPlayerStatisticsSnapshotV1(
            snapshot_id=" snapshot-a",
            observed_at="2026-07-23T10:00:00Z",
            statistics_record=record,
        )


def test_snapshot_and_participant_defensively_copy_nested_immutable_values() -> None:
    record = _statistics_record()
    snapshot = MatchPlayerStatisticsSnapshotV1(
        snapshot_id="snapshot-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=record,
    )
    participant = MatchParticipantV1(
        player_id="player-a",
        player_label=None,
        platform_player_id=None,
        table_place="place_1",
        statistics_snapshot=snapshot,
    )
    object.__setattr__(record, "player_id", "changed-record")
    object.__setattr__(snapshot, "snapshot_id", "changed-snapshot")
    assert participant.statistics_snapshot.snapshot_id == "snapshot-a"
    assert participant.statistics_snapshot.statistics_record.player_id == "player-a"
    with pytest.raises(FrozenInstanceError):
        participant.statistics_snapshot.observed_at = "changed"


def test_snapshot_serialization_reuses_opponent_serializer_without_derivation(
    monkeypatch,
) -> None:
    import skat_ai.opponent_statistics as statistics_module

    def unexpected_derivation(*_args, **_kwargs):
        raise AssertionError("Snapshot serialization derived a Player Profile.")

    monkeypatch.setattr(
        statistics_module,
        "derive_opponent_profile",
        unexpected_derivation,
    )
    record = _statistics_record()
    snapshot = MatchPlayerStatisticsSnapshotV1(
        snapshot_id="snapshot-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=record,
    )
    existing = build_serializable_opponent_statistics_input(
        OpponentStatisticsInput(
            schema_version=1,
            records=(record,),
        )
    )["opponent_statistics_input"]["records"][0]
    assert snapshot.to_dict()["statistics_record"] == existing
    assert record.player_id == snapshot.statistics_record.player_id


def test_participant_validates_identity_labels_place_and_nullable_fields() -> None:
    participant = MatchParticipantV1(
        player_id="player-a",
        player_label=None,
        platform_player_id=None,
        table_place="place_1",
        statistics_snapshot=None,
    )
    assert participant.to_dict() == {
        "player_id": "player-a",
        "player_label": None,
        "platform_player_id": None,
        "table_place": "place_1",
        "statistics_snapshot": None,
    }
    assert {"hand", "seat", "role", "result"}.isdisjoint(participant.to_dict())
    for player_id in ("", " player-a", "me", "left", "right"):
        with pytest.raises(ValueError):
            MatchParticipantV1(
                player_id=player_id,
                player_label=None,
                platform_player_id=None,
                table_place="place_1",
                statistics_snapshot=None,
            )
    with pytest.raises(ValueError, match="table_place"):
        MatchParticipantV1(
            player_id="player-a",
            player_label=None,
            platform_player_id=None,
            table_place="forehand",
            statistics_snapshot=None,
        )


def test_participant_reconciles_snapshot_player_identity_and_label() -> None:
    with pytest.raises(ValueError, match="Player identity"):
        MatchParticipantV1(
            player_id="player-b",
            player_label=None,
            platform_player_id=None,
            table_place="place_2",
            statistics_snapshot=_snapshot("player-a"),
        )

    raw_record = build_valid_record()
    raw_record["player_id"] = "player-a"
    conflicting = MatchPlayerStatisticsSnapshotV1(
        snapshot_id="snapshot-a",
        observed_at="2026-07-23T10:00:00Z",
        statistics_record=build_opponent_statistics_input(
            {"schema_version": 1, "records": [raw_record]}
        ).records[0],
    )
    with pytest.raises(ValueError, match="conflicting non-null"):
        MatchParticipantV1(
            player_id="player-a",
            player_label="Different Label",
            platform_player_id=None,
            table_place="place_1",
            statistics_snapshot=conflicting,
        )


def test_match_capture_accepts_youtube_and_manual_sources_with_nullable_metadata() -> None:
    youtube = _capture()
    manual = _capture(
        external_match_id=None,
        played_at=None,
        source=MatchSourceMetadataV1(
            source_kind="manual_observation",
            source_url=None,
            source_title="Manual post-game observation",
            source_channel_name=None,
            match_timecode=None,
        ),
    )
    assert youtube.tournament_format is EUROSKAT_36_STANDARD_V1_FORMAT
    assert youtube.source.source_kind == "youtube_video"
    assert manual.external_match_id is None
    assert manual.played_at is None
    assert manual.source.source_kind == "manual_observation"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("match_id", " match", "leading or trailing"),
        ("title", "", "non-empty string"),
        ("game_platform", "EuroSkat ", "leading or trailing"),
        ("external_match_id", " ", "non-empty string"),
        ("played_at", "2026-08-09", "RFC 3339"),
    ),
)
def test_match_capture_validates_identity_and_descriptive_metadata(
    field_name: str,
    value,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _capture(**{field_name: value})


@pytest.mark.parametrize("participant_count", (2, 4))
def test_match_capture_requires_exactly_three_participants(participant_count: int) -> None:
    participants = list(_participants(snapshots=False))
    if participant_count == 2:
        participants.pop()
    else:
        participants.append(
            MatchParticipantV1(
                player_id="player-d",
                player_label=None,
                platform_player_id=None,
                table_place="place_3",
                statistics_snapshot=None,
            )
        )
    with pytest.raises(ValueError, match="exactly 3"):
        _capture(participants=participants)


def test_match_capture_requires_canonical_table_place_order() -> None:
    participants = list(_participants(snapshots=False))
    participants[0], participants[1] = participants[1], participants[0]
    with pytest.raises(ValueError, match="canonical order"):
        _capture(participants=participants)
    assert tuple(participant.table_place for participant in _capture().participants) == (
        FIXED_THREE_PLAYER_LIST_TABLE_PLACES
    )


def test_match_capture_rejects_duplicate_player_platform_and_snapshot_ids() -> None:
    duplicate_player = list(_participants(snapshots=False))
    duplicate_player[1] = MatchParticipantV1(
        player_id="player-a",
        player_label=None,
        platform_player_id="platform-b",
        table_place="place_2",
        statistics_snapshot=None,
    )
    with pytest.raises(ValueError, match="Player IDs must be unique"):
        _capture(participants=duplicate_player)

    duplicate_platform = list(_participants(snapshots=False))
    duplicate_platform[1] = MatchParticipantV1(
        player_id="player-b",
        player_label=None,
        platform_player_id="platform-a",
        table_place="place_2",
        statistics_snapshot=None,
    )
    with pytest.raises(ValueError, match="platform_player_id"):
        _capture(participants=duplicate_platform)

    duplicate_snapshot = tuple(
        MatchParticipantV1(
            player_id=f"player-{letter}",
            player_label=None,
            platform_player_id=None,
            table_place=f"place_{index}",
            statistics_snapshot=(
                _snapshot(f"player-{letter}", "shared-snapshot")
                if index < 3
                else None
            ),
        )
        for index, letter in enumerate("abc", start=1)
    )
    with pytest.raises(ValueError, match="snapshot_id"):
        _capture(participants=duplicate_snapshot)


@pytest.mark.parametrize("perspective", ("player-a", "player-b", "player-c"))
def test_match_perspective_is_any_one_exact_participant(perspective: str) -> None:
    capture = _capture(perspective_player_id=perspective)
    assert capture.perspective_player_id == perspective


@pytest.mark.parametrize("perspective", ("unknown", "me", "left", "right", None))
def test_match_perspective_rejects_missing_unknown_or_relative_identity(
    perspective,
) -> None:
    with pytest.raises(ValueError, match="perspective_player_id"):
        _capture(perspective_player_id=perspective)


def test_match_capture_rejects_noncanonical_format_count_override() -> None:
    forged = MatchTournamentFormatV1(
        format_id="euroskat_36_standard_v1",
        provider="EuroSkat",
        display_name="36er Standard",
        player_count=3,
        game_count=18,
    )
    with pytest.raises(ValueError, match="exact canonical"):
        _capture(tournament_format=forged)


def test_match_capture_is_frozen_slotted_keyword_only_with_exact_fields() -> None:
    capture = _capture()
    assert [field.name for field in fields(capture)] == [
        "match_capture_contract_version",
        "match_id",
        "title",
        "game_platform",
        "external_match_id",
        "played_at",
        "tournament_format",
        "source",
        "participants",
        "perspective_player_id",
    ]
    assert not hasattr(capture, "__dict__")
    with pytest.raises(FrozenInstanceError):
        capture.title = "Changed"
    with pytest.raises(TypeError):
        MatchCaptureDefinitionV1("match", "title")


def test_match_serialization_is_deterministic_defensive_and_metadata_only() -> None:
    source = _youtube_source()
    participants = list(_participants())
    capture = _capture(source=source, participants=participants)
    participants.clear()
    object.__setattr__(source, "source_title", "Caller mutation")

    first = capture.to_dict()
    second = capture.to_dict()
    first["source"]["match_timecode"]["start_offset_ms"] = 999
    first["participants"][0]["statistics_snapshot"]["statistics_record"][
        "games_played"
    ] = 1
    assert second["source"]["source_title"] == "EuroSkat 36er Standard Match"
    assert second["source"]["match_timecode"]["start_offset_ms"] == 12_345
    assert second["participants"][0]["statistics_snapshot"][
        "statistics_record"
    ]["games_played"] == 127
    assert len(capture.participants) == 3
    assert list(second) == [
        "match_capture_contract_version",
        "match_id",
        "title",
        "game_platform",
        "external_match_id",
        "played_at",
        "tournament_format",
        "source",
        "participants",
        "perspective_player_id",
    ]
    forbidden = {
        "application_user_id",
        "cards",
        "hand",
        "skat",
        "discards",
        "plays",
        "games",
        "comments",
        "path",
        "created_at",
    }
    assert forbidden.isdisjoint(second)
    json.dumps(second)


def test_existing_internal_public_package_and_count_contracts_are_unchanged() -> None:
    historical_list = build_fixed_three_player_historical_list(build_list_input())
    assert len(historical_list.entries) == 36
    assert FIXED_THREE_PLAYER_LIST_TABLE_PLACES == (
        "place_1",
        "place_2",
        "place_3",
    )
    assert SessionPlayerV1(
        player_id="player-a",
        player_label=None,
        seat="forehand",
    ).to_dict() == {
        "player_id": "player-a",
        "player_label": None,
        "seat": "forehand",
    }
    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert "MatchCaptureDefinitionV1" not in api_v1.__all__
    assert "MatchCaptureDefinitionV1" not in session_api.__all__
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 70
    assert len(
        tuple(
            (PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob(
                "*.schema.json"
            )
        )
    ) == 70
    assert len(SCENARIOS) == 96
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == "0.16.0"
    assert skat_ai.__version__ == "0.16.0"
