"""Freshness/sign checks (C-DOC-04/05/06)."""

from datetime import date


def parse_date(raw: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def coi_status(expiry_raw: str, today: date, warn_days: int = 30) -> str:
    exp = parse_date(expiry_raw)
    if exp is None:
        return "UNKNOWN"
    if exp < today:
        return "EXPIRED"
    if (exp - today).days <= warn_days:
        return "EXPIRING_SOON"
    return "VALID"


def bank_letter_stale(letter_date_raw: str, today: date, max_days: int = 365) -> bool:
    d = parse_date(letter_date_raw)
    return d is None or (today - d).days > max_days
