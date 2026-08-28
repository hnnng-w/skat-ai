import re
from datetime import datetime, timedelta

_RFC_3339_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)


def parse_rfc3339_datetime(value: str, field_name: str) -> datetime:
    """Parses one offset-aware RFC 3339 timestamp without rewriting its source text."""
    error_message = f"{field_name} must be a valid RFC 3339 date-time with a time-zone offset."
    if not _RFC_3339_DATE_TIME.fullmatch(value):
        raise ValueError(error_message)

    normalized_value = value.replace("t", "T").replace("z", "+00:00").replace("Z", "+00:00")
    leap_second = normalized_value[17:19] == "60"
    if leap_second:
        normalized_value = f"{normalized_value[:17]}59{normalized_value[19:]}"
    try:
        parsed = datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(error_message) from error
    return parsed + timedelta(seconds=1) if leap_second else parsed
