"""Virtual clock (backed by clock_state; NULL initializes, never silent)."""

from datetime import datetime, timezone

from backend.app.persistence import models
from backend.app.persistence.store import session


def get_virtual_now() -> datetime:
    with session() as s:
        row = s.get(models.ClockState, "clock")
        if row is None or row.virtual_now is None:
            now = datetime.now(timezone.utc)
            s.add(models.ClockState(id="clock", virtual_now=now))
            return now
        ts = row.virtual_now
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def advance_virtual_now(days: int) -> datetime:
    if days <= 0:
        raise ValueError("days must be > 0")
    from datetime import timedelta

    with session() as s:
        row = s.get(models.ClockState, "clock")
        if row is None or row.virtual_now is None:
            base = datetime.now(timezone.utc)
        else:
            base = row.virtual_now
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
        new = base + timedelta(days=days)
        if row is None:
            s.add(models.ClockState(id="clock", virtual_now=new))
        else:
            row.virtual_now = new
        return new


class VirtualClock:
    def now(self) -> datetime:
        return get_virtual_now()
