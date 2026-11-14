"""Timezone and Datetime Utilities.
Ensures consistent UTC storage in the database, ISO-8601 UTC serialization,
and localized, unambiguous display formatting (defaulting to Asia/Kolkata / IST).
"""

from datetime import datetime, timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo
import re

DEFAULT_TIMEZONE = "Asia/Kolkata"

TIMEZONE_ABBREVIATIONS = {
    "Asia/Kolkata": "IST",
    "Asia/Calcutta": "IST",
    "UTC": "UTC",
    "GMT": "GMT",
    "Europe/London": "BST",
    "America/New_York": "EST",
    "America/Los_Angeles": "PST",
    "America/Chicago": "CST",
    "Asia/Singapore": "SGT",
    "Asia/Tokyo": "JST",
    "Asia/Dubai": "GST",
    "Australia/Sydney": "AEST"
}

# Regex to detect already formatted unambiguous timestamps
ALREADY_FORMATTED_RE = re.compile(
    r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4},\s+\d{2}:\d{2}:\d{2}\s+(?:AM|PM)\s+[A-Z0-9+-]+$"
)


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serializes a datetime object into a standard ISO-8601 UTC string with trailing 'Z'.

    Preserves the exact UTC timestamp in the database while giving API consumers
    an explicit, unambiguous UTC indicator.
    """
    if dt is None:
        return None

    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        # Naive datetime from database is stored in UTC
        iso = dt.isoformat()
        return f"{iso}Z" if not iso.endswith("Z") else iso

    # Timezone-aware datetime: convert to UTC
    utc_dt = dt.astimezone(timezone.utc)
    iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%S")
    if utc_dt.microsecond:
        iso += f".{utc_dt.microsecond:06d}"
    return f"{iso}Z"


def parse_to_utc_datetime(dt_or_str: Union[datetime, str, None]) -> Optional[datetime]:
    """Safely parses a datetime or string into a timezone-aware UTC datetime.

    Handles ISO-8601 strings with or without 'Z', SQL format strings, and datetime instances.
    Safely returns None for invalid or missing inputs.
    """
    if dt_or_str is None:
        return None

    if isinstance(dt_or_str, datetime):
        if dt_or_str.tzinfo is None:
            return dt_or_str.replace(tzinfo=timezone.utc)
        return dt_or_str.astimezone(timezone.utc)

    if not isinstance(dt_or_str, str):
        return None

    s = dt_or_str.strip()
    if not s:
        return None

    # Handle standard ISO strings
    # If ends with Z
    clean_s = s
    if clean_s.endswith("Z"):
        clean_s = clean_s[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(clean_s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass

    # Fallback to standard SQL format
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

    return None


def utc_to_timezone(dt: Optional[datetime], tz_name: str = DEFAULT_TIMEZONE) -> Optional[datetime]:
    """Converts a UTC datetime to a specified target timezone (default Asia/Kolkata)."""
    if dt is None:
        return None

    utc_dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    try:
        target_tz = ZoneInfo(tz_name)
    except Exception:
        target_tz = ZoneInfo(DEFAULT_TIMEZONE)

    return utc_dt.astimezone(target_tz)


def format_display_datetime(
    dt_or_str: Union[datetime, str, None],
    tz_name: str = DEFAULT_TIMEZONE,
    fallback: str = "--"
) -> str:
    """Formats a UTC timestamp into the user's local timezone in the unambiguous format:

    '12 Nov 2026, 10:36:39 AM IST'

    Requirements handled:
    - Default timezone: Asia/Kolkata (IST)
    - Unambiguous format: DD Mon YYYY, hh:mm:ss AM/PM TZ
    - Safe handling of missing / invalid inputs
    - Double timezone conversion prevention
    """
    if dt_or_str is None:
        return fallback

    if isinstance(dt_or_str, str):
        trimmed = dt_or_str.strip()
        if not trimmed:
            return fallback
        # Check if already formatted to prevent double conversion
        if ALREADY_FORMATTED_RE.match(trimmed):
            return trimmed

    utc_dt = parse_to_utc_datetime(dt_or_str)
    if utc_dt is None:
        return fallback

    try:
        target_tz = ZoneInfo(tz_name)
    except Exception:
        target_tz = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE

    local_dt = utc_dt.astimezone(target_tz)

    # Determine timezone abbreviation
    tz_abbr = TIMEZONE_ABBREVIATIONS.get(tz_name)
    if not tz_abbr:
        tz_abbr = local_dt.strftime("%Z")
        if not tz_abbr or tz_abbr.startswith("+") or tz_abbr.startswith("-"):
            tz_abbr = tz_name

    # Format: 12 Nov 2026, 10:36:39 AM IST
    # Day %d is 2-digit zero-padded, or e.g. 12
    return local_dt.strftime(f"%d %b %Y, %I:%M:%S %p {tz_abbr}")


def format_display_date(
    dt_or_str: Union[datetime, str, None],
    tz_name: str = DEFAULT_TIMEZONE,
    fallback: str = "--"
) -> str:
    """Formats a UTC timestamp into an unambiguous date string (e.g., '12 Nov 2026')."""
    if dt_or_str is None:
        return fallback

    utc_dt = parse_to_utc_datetime(dt_or_str)
    if utc_dt is None:
        return fallback

    try:
        target_tz = ZoneInfo(tz_name)
    except Exception:
        target_tz = ZoneInfo(DEFAULT_TIMEZONE)

    local_dt = utc_dt.astimezone(target_tz)
    return local_dt.strftime("%d %b %Y")

