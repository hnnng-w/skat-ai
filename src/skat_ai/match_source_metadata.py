from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urlsplit

from skat_ai.performance_rating import (
    validate_stable_list_entry_identifier,
    validate_stable_list_player_label,
)

MATCH_SOURCE_METADATA_VERSION = 1
MEDIA_TIMECODE_VERSION = 1

MATCH_SOURCE_KINDS: Final[tuple[str, ...]] = (
    "youtube_video",
    "other_video",
    "manual_observation",
)


def _require_version(value: object, expected: int, field_name: str) -> None:
    if type(value) is not int or value != expected:
        raise ValueError(f"{field_name} must equal {expected}.")


def _validate_source_url(value: object, field_name: str) -> None:
    validate_stable_list_entry_identifier(value, field_name)
    assert isinstance(value, str)
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as error:
        raise ValueError(f"{field_name} must be an absolute HTTP or HTTPS URL.") from error
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or hostname is None
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"{field_name} must be an absolute HTTP or HTTPS URL.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaTimecodeV1:
    """Millisecond bounds within one caller-identified media source."""

    media_timecode_version: int = MEDIA_TIMECODE_VERSION
    start_offset_ms: int
    end_offset_ms: int | None

    def __post_init__(self) -> None:
        _require_version(
            self.media_timecode_version,
            MEDIA_TIMECODE_VERSION,
            "media_timecode_version",
        )
        if type(self.start_offset_ms) is not int or self.start_offset_ms < 0:
            raise ValueError("start_offset_ms must be a non-negative integer.")
        if self.end_offset_ms is not None:
            if type(self.end_offset_ms) is not int or self.end_offset_ms < 0:
                raise ValueError("end_offset_ms must be null or a non-negative integer.")
            if self.end_offset_ms < self.start_offset_ms:
                raise ValueError("end_offset_ms must not precede start_offset_ms.")

    def to_dict(self) -> dict[str, int | None]:
        return {
            "media_timecode_version": self.media_timecode_version,
            "start_offset_ms": self.start_offset_ms,
            "end_offset_ms": self.end_offset_ms,
        }


def _copy_media_timecode(value: MediaTimecodeV1 | None) -> MediaTimecodeV1 | None:
    if value is None:
        return None
    if not isinstance(value, MediaTimecodeV1):
        raise ValueError("match_timecode must be null or MediaTimecodeV1.")
    return MediaTimecodeV1(
        media_timecode_version=value.media_timecode_version,
        start_offset_ms=value.start_offset_ms,
        end_offset_ms=value.end_offset_ms,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchSourceMetadataV1:
    """Descriptive Match source metadata without source-system integration."""

    match_source_metadata_version: int = MATCH_SOURCE_METADATA_VERSION
    source_kind: str
    source_url: str | None
    source_title: str
    source_channel_name: str | None
    match_timecode: MediaTimecodeV1 | None

    def __post_init__(self) -> None:
        _require_version(
            self.match_source_metadata_version,
            MATCH_SOURCE_METADATA_VERSION,
            "match_source_metadata_version",
        )
        if self.source_kind not in MATCH_SOURCE_KINDS:
            raise ValueError(f"source_kind must be one of {list(MATCH_SOURCE_KINDS)}.")
        validate_stable_list_player_label(self.source_title, "source_title")
        if self.source_channel_name is not None:
            validate_stable_list_player_label(
                self.source_channel_name,
                "source_channel_name",
            )

        if self.source_kind in {"youtube_video", "other_video"}:
            if self.source_url is None:
                raise ValueError(f"source_url is required for {self.source_kind}.")
            _validate_source_url(self.source_url, "source_url")
        else:
            if self.source_url is not None:
                raise ValueError("source_url must be null for manual_observation.")
            if self.source_channel_name is not None:
                raise ValueError(
                    "source_channel_name must be null for manual_observation."
                )

        object.__setattr__(self, "match_timecode", _copy_media_timecode(self.match_timecode))

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_source_metadata_version": self.match_source_metadata_version,
            "source_kind": self.source_kind,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_channel_name": self.source_channel_name,
            "match_timecode": (
                None if self.match_timecode is None else self.match_timecode.to_dict()
            ),
        }


def copy_match_source_metadata_v1(value: MatchSourceMetadataV1) -> MatchSourceMetadataV1:
    """Returns a validated defensive copy of one immutable source value."""
    if not isinstance(value, MatchSourceMetadataV1):
        raise ValueError("source must be MatchSourceMetadataV1.")
    return MatchSourceMetadataV1(
        match_source_metadata_version=value.match_source_metadata_version,
        source_kind=value.source_kind,
        source_url=value.source_url,
        source_title=value.source_title,
        source_channel_name=value.source_channel_name,
        match_timecode=value.match_timecode,
    )
