"""Display dates in the app's one style: "Wed, Oct 14", with the year only when it isn't the data year."""
import re
from datetime import date, datetime

from . import db

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOCAL = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?[+-]\d{2}:\d{2}$")   # local time with an offset


def day(d: date, year: bool | None = None) -> str:
    """date -> "Wed, Oct 14" (or "Mon, Dec 15, 2025" outside the data year, or when year=True)."""
    if year is None:
        year = d.year != db.as_of().year
    return f"{d:%a}, {d:%b} {d.day}" + (f", {d.year}" if year else "")


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
