"""Display dates in the app's one style: "Wed, Oct 14", with the year only when it isn't the data year."""
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import db

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOCAL = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?[+-]\d{2}:\d{2}$")   # local time with an offset


def day(d: date, year: bool | None = None) -> str:
    """date -> "Wed, Oct 14" (or "Mon, Dec 15, 2025" outside the data year, or when year=True)."""
    if year is None:
        year = d.year != db.as_of().year
    return f"{d:%a}, {d:%b} {d.day}" + (f", {d.year}" if year else "")


def as_of_central(dt: datetime | None = None) -> str:
    """The data's as-of time the way the app shows it: "Sun, Oct 11, 4:00 PM Central" (CDT or CST)."""
    t = (dt or db.as_of()).astimezone(ZoneInfo("America/Chicago"))
    return f"{day(t.date())}, {t.strftime('%I:%M %p').lstrip('0')} Central"


US_ZONES = {  # U.S. and Canadian zones by their common names; elsewhere the city ('Shanghai time')
    "America/New_York": "Eastern", "America/Detroit": "Eastern", "America/Indiana/Indianapolis": "Eastern",
    "America/Toronto": "Eastern", "America/Chicago": "Central", "America/Winnipeg": "Central",
    "America/Denver": "Mountain", "America/Boise": "Mountain", "America/Edmonton": "Mountain",
    "America/Phoenix": "Mountain (Arizona)", "America/Los_Angeles": "Pacific", "America/Vancouver": "Pacific",
    "America/Tijuana": "Pacific", "America/Halifax": "Atlantic", "America/Anchorage": "Alaska",
    "Pacific/Honolulu": "Hawaii", "America/Honolulu": "Hawaii"}


def zone_name(tz: str | None) -> str | None:
    """'America/New_York' -> 'Eastern'; outside the U.S. the city: 'Asia/Shanghai' -> 'Shanghai time'."""
    if not tz:
        return None
    return US_ZONES.get(tz) or tz.split("/")[-1].replace("_", " ") + " time"


def display_local(value: str, tz: str | None, where: str) -> str | None:
    """A local date-time with its zone named: 'Wed, Oct 14, 5:00 AM Eastern (ATL local time)'. Without a known zone,
    the UTC offset is named instead, so a time is never shown as Central by mistake."""
    shown = display(value)
    if not shown or not _LOCAL.match(value):
        return shown
    zone = zone_name(tz)
    if zone:
        return f"{shown} {zone} ({where} local time)"
    off = datetime.fromisoformat(value).strftime("%z")
    return f"{shown} ({where} local time, UTC{off[:3]}:{off[3:]})"


def display(value) -> str | None:
    """A display string for an ISO date or a local date-time with an offset; None for anything else
    (UTC stamps are skipped: replies use local times, which have their own fields)."""
    if not isinstance(value, str):
        return None
    if _DATE.match(value):
        return day(date.fromisoformat(value))
    if _LOCAL.match(value):
        t = datetime.fromisoformat(value)
        hour = t.strftime("%I:%M %p").lstrip("0")
        return f"{day(t.date())}, {hour}"
    return None
