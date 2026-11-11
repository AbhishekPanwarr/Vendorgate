"""DB-backed check cache (CheckCacheRow); survives restarts for delta runs."""

from backend.app.domain.models import Finding
from backend.app.persistence.store import session


class DbCheckCache:
    def get(self, fp: str) -> list[Finding] | None:
        from backend.app.persistence import models

        with session() as s:
            row = s.get(models.CheckCacheRow, fp)
            if row is None or not isinstance(row.result, list):
                return None
            return [Finding.model_validate(f) for f in row.result]

    def put(self, fp: str, findings: list[Finding]) -> None:
        from typing import Any

        from backend.app.persistence import models

        with session() as s:
            row = s.get(models.CheckCacheRow, fp)
            data: list[Any] = [f.model_dump(mode="json") for f in findings]
            check_id = findings[0].check_id if findings else ""
            if row is None:
                s.add(models.CheckCacheRow(fingerprint=fp, check_id=check_id,
                                           result=data))
            else:
                setattr(row, "result", data)
                setattr(row, "check_id", check_id)