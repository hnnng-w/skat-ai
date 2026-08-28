from __future__ import annotations

import re

from skatmind.match_source_metadata import MediaTimecodeV1

_TIMECODE_PATTERN = re.compile(
    r"(?P<body>\d+|\d+:\d{2}|\d+:\d{2}:\d{2})(?:\.(?P<milliseconds>\d{3}))?"
)


def parse_presentation_timecode_v1(value: object) -> int | None:
    """Parses blank, SS, MM:SS, or HH:MM:SS.mmm into exact milliseconds."""
    if not isinstance(value, str):
        raise ValueError("timecode must be text.")
    if value == "":
        return None
    if value != value.strip():
        raise ValueError("timecode must not contain surrounding whitespace.")
    matched = _TIMECODE_PATTERN.fullmatch(value)
    if matched is None:
        raise ValueError("timecode must use SS, MM:SS, or HH:MM:SS with optional .mmm.")
    components = tuple(int(component) for component in matched.group("body").split(":"))
    if len(components) == 1:
        hours, minutes, seconds = 0, 0, components[0]
    elif len(components) == 2:
        hours, minutes, seconds = 0, *components
    else:
        hours, minutes, seconds = components
    if seconds >= 60:
        raise ValueError("timecode seconds must be less than 60.")
    if len(components) == 3 and minutes >= 60:
        raise ValueError("timecode minutes must be less than 60.")
    milliseconds = int(matched.group("milliseconds") or "0")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def format_presentation_timecode_v1(value: int | None) -> str:
    """Formats exact milliseconds deterministically for browser presentation."""
    if value is None:
        return ""
    if type(value) is not int or value < 0:
        raise ValueError("timecode milliseconds must be a non-negative integer or null.")
    total_seconds, milliseconds = divmod(value, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        result = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes:
        result = f"{minutes:02d}:{seconds:02d}"
    else:
        result = str(seconds)
    return f"{result}.{milliseconds:03d}" if milliseconds else result


def build_presentation_timecode_v1(
    start: object,
    end: object = "",
) -> MediaTimecodeV1 | None:
    start_ms = parse_presentation_timecode_v1(start)
    end_ms = parse_presentation_timecode_v1(end)
    if start_ms is None:
        if end_ms is not None:
            raise ValueError("A timecode end requires a start.")
        return None
    return MediaTimecodeV1(start_offset_ms=start_ms, end_offset_ms=end_ms)


def format_media_timecode_v1(value: MediaTimecodeV1 | None) -> dict[str, str]:
    if value is None:
        return {"start": "", "end": ""}
    return {
        "start": format_presentation_timecode_v1(value.start_offset_ms),
        "end": format_presentation_timecode_v1(value.end_offset_ms),
    }
