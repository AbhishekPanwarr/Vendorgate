"""SQLite-backed store with the same dict-like partitions as the old STORE.

Partitions: cases, runs, events, idempotency, callbacks, docs.
Survives restarts; this is what nudge idempotency, retry counters, appeal
state, and delta memoization read.
"""

import base64
import os
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy.orm import Session

from backend.app.persistence import models
from backend.app.persistence.db import get_engine
from backend.app.persistence.models import Base

_engines: dict[str, Any] = {}


def _url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///data/vendorgate.db")


def _engine() -> Any:
    url = _url()
    if url not in _engines:
        eng = get_engine(url)
        Base.metadata.create_all(eng)
        _engines[url] = eng
    return _engines[url]


@contextmanager
def session() -> Iterator[Session]:
    from sqlalchemy.orm import sessionmaker

    sm = sessionmaker(bind=_engine(), future=True)
    s = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def reset_db() -> None:
    with session() as s:
        for table in reversed(Base.metadata.sorted_tables):
            s.execute(table.delete())


# ---- row <-> dict mapping ----

_CASE_FIELDS = (
    "case_id",
    "run_id",
    "requester",
    "submission_type",
    "existing_vendor_id",
    "status",
    "tier",
    "score",
    "reason_codes",
    "vendor_id",
)


def _case_to_dict(row: models.Case) -> dict[str, Any]:
    return {
        "case_id": row.id,
        "run_id": row.run_id,
        "requester": row.requester,
        "submission_type": row.submission_type,
        "existing_vendor_id": row.existing_vendor_id,
        "status": row.status,
        "tier": row.tier,
        "score": row.score,
        "reason_codes": row.reason_codes if isinstance(row.reason_codes, list) else [],
        "vendor_id": row.vendor_id,
        "current_version": row.current_version,
    }


class _CasesPartition:
    def get(self, key: str, default: Any = None) -> Any:
        with session() as s:
            row = s.get(models.Case, key)
            return _case_to_dict(row) if row else default

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        set_case(value)

    def __contains__(self, key: object) -> bool:
        return self.get(str(key)) is not None

    def values(self) -> list[dict[str, Any]]:
        with session() as s:
            return [_case_to_dict(r) for r in s.query(models.Case).all()]

    def clear(self) -> None:
        with session() as s:
            s.query(models.Case).delete()


def set_case(value: dict[str, Any]) -> None:
    from datetime import datetime, timedelta, timezone

    with session() as s:
        row = s.get(models.Case, str(value["case_id"]))
        now = datetime.now(timezone.utc)
        data = {
            "id": str(value["case_id"]),
            "run_id": value.get("run_id"),
            "requester": str(value.get("requester") or ""),
            "submission_type": str(value.get("submission_type") or "NEW_VENDOR"),
            "existing_vendor_id": value.get("existing_vendor_id"),
            "status": value.get("status"),
            "tier": value.get("tier"),
            "score": value.get("score") or 0.0,
            "reason_codes": value.get("reason_codes") or [],
            "vendor_id": value.get("vendor_id"),
        }
        if row is None:
            s.add(
                models.Case(
                    **data,
                    opened_at=now,
                    due_at=now + timedelta(days=14),
                    current_version=int(value.get("current_version", 1)),
                )
            )
        else:
            for k, v in data.items():
                setattr(row, k, v)
            if "current_version" in value:
                row.current_version = int(value["current_version"])


def append_case_event(
    case_id: str, type: str, payload: dict[str, Any], actor: str = "system"
) -> dict[str, Any]:
    from backend.app.persistence.audit_chain import append_event

    with session() as s:
        last = (
            s.query(models.CaseEvent)
            .filter_by(case_id=case_id)
            .order_by(models.CaseEvent.seq.desc())
            .first()
        )
        prev = last.entry_hash if last else "GENESIS"
        seq = (last.seq + 1) if last else 1
        from datetime import datetime, timezone

        e = append_event(
            case_id, seq, datetime.now(timezone.utc).isoformat(), actor, type, payload, prev
        )
        s.add(
            models.CaseEvent(
                case_id=case_id,
                seq=seq,
                actor=actor,
                type=type,
                payload=payload,
                prev_hash=e["prev_hash"],
                entry_hash=e["entry_hash"],
            )
        )
        return e


def case_events(case_id: str, type: str | None = None) -> list[dict[str, Any]]:
    with session() as s:
        q = s.query(models.CaseEvent).filter_by(case_id=case_id).order_by(models.CaseEvent.seq)
        if type:
            q = q.filter_by(type=type)
        return [
            {
                "seq": r.seq,
                "type": r.type,
                "payload": r.payload,
                "actor": r.actor,
                "entry_hash": r.entry_hash,
            }
            for r in q.all()
        ]


class _RunsPartition:
    def get(self, key: str, default: Any = None) -> Any:
        with session() as s:
            row = s.get(models.Run, key)
            if row is None or not row.result:
                return default
            return dict(row.result)

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        set_run(key, value)

    def __contains__(self, key: object) -> bool:
        return self.get(str(key)) is not None

    def clear(self) -> None:
        with session() as s:
            s.query(models.Run).delete()


def set_run(run_id: str, value: dict[str, Any]) -> None:
    with session() as s:
        row = s.get(models.Run, run_id)
        if row is None:
            row = models.Run(
                id=run_id, case_id=str(value.get("case_id", "")), submission_version_id=""
            )
            s.add(row)
        row.case_id = str(value.get("case_id", row.case_id or ""))
        row.mode = str(value.get("mode", "FULL"))
        row.result = dict(value)


class _EventsPartition:
    def get(self, key: str, default: Any = None) -> Any:
        with session() as s:
            rows = (
                s.query(models.RunEvent).filter_by(run_id=key).order_by(models.RunEvent.seq).all()
            )
            if not rows:
                return default
            return [{"seq": r.seq, "type": r.type, "data": r.data} for r in rows]

    def __setitem__(self, key: str, value: list[dict[str, Any]]) -> None:
        with session() as s:
            s.query(models.RunEvent).filter_by(run_id=key).delete()
            for e in value:
                s.add(
                    models.RunEvent(
                        run_id=key,
                        seq=int(e.get("seq", 0)),
                        type=str(e.get("type", "")),
                        data=e.get("data") or {},
                    )
                )

    def clear(self) -> None:
        with session() as s:
            s.query(models.RunEvent).delete()


class _IdempotencyPartition:
    def get(self, key: str, default: Any = None) -> Any:
        with session() as s:
            row = s.get(models.IdempotencyKey, key)
            if row is None:
                return default
            if row.response:
                return dict(row.response)
            return {"case_id": row.case_id, "run_id": row.run_id}

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        with session() as s:
            row = s.get(models.IdempotencyKey, key)
            if row is None:
                s.add(
                    models.IdempotencyKey(
                        key=key,
                        case_id=str(value.get("case_id", "")),
                        run_id=str(value.get("run_id", "")),
                        response=dict(value),
                    )
                )

    def __contains__(self, key: object) -> bool:
        return self.get(str(key)) is not None

    def clear(self) -> None:
        with session() as s:
            s.query(models.IdempotencyKey).delete()


class _AppendList(list):  # type: ignore[type-arg]
    def __init__(self, sink: Any) -> None:
        self._sink = sink

    def append(self, value: Any) -> None:
        self._sink(value)


class _CallbacksPartition:
    def setdefault(self, key: str, default: Any = None) -> Any:
        return _AppendList(self._insert)

    def _insert(self, value: dict[str, Any]) -> None:
        with session() as s:
            s.add(
                models.Callback(
                    case_id=str(value.get("case_id", "")),
                    number_used=str(value.get("number_used", "")),
                    number_source=str(value.get("number_source", "")),
                    outcome=str(value.get("outcome", "")),
                    independent=bool(value.get("independent")),
                    actor=str(value.get("actor", "")),
                    attested=bool(value.get("attested")),
                )
            )

    def all(self) -> list[dict[str, Any]]:
        with session() as s:
            return [
                {
                    "case_id": r.case_id,
                    "number_used": r.number_used,
                    "number_source": r.number_source,
                    "outcome": r.outcome,
                    "independent": r.independent,
                    "actor": r.actor,
                    "attested": r.attested,
                }
                for r in s.query(models.Callback).all()
            ]

    def clear(self) -> None:
        with session() as s:
            s.query(models.Callback).delete()


class _DocsPartition:
    def get(self, key: str, default: Any = None) -> Any:
        with session() as s:
            rows = s.query(models.CaseDoc).filter_by(run_id=key).all()
            if not rows:
                return default
            import base64 as _b64

            return {r.doc_id: [r.filename, _b64.b64encode(r.data or b"").decode()] for r in rows}

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        import base64 as _b64

        with session() as s:
            s.query(models.CaseDoc).filter_by(run_id=key).delete()
            run = s.get(models.Run, key)
            case_id = run.case_id if run else ""
            for doc_id, (fn, b64) in (value or {}).items():
                s.add(
                    models.CaseDoc(
                        case_id=case_id,
                        run_id=key,
                        doc_id=doc_id,
                        filename=fn,
                        sha256="",
                        data=_b64.b64decode(b64),
                    )
                )

    def clear(self) -> None:
        with session() as s:
            s.query(models.CaseDoc).delete()


class SQLiteStore:
    def __init__(self) -> None:
        self.cases = _CasesPartition()
        self.runs = _RunsPartition()
        self.events = _EventsPartition()
        self.idempotency = _IdempotencyPartition()
        self.callbacks = _CallbacksPartition()
        self.docs = _DocsPartition()

    def __getitem__(self, key: str) -> Any:
        return {
            "cases": self.cases,
            "runs": self.runs,
            "events": self.events,
            "idempotency": self.idempotency,
            "callbacks": self.callbacks,
            "docs": self.docs,
        }[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key == "callbacks":
            return self.callbacks.setdefault(key, default)
        if key == "docs":
            return self.docs
        return self[key]


def _b64_str(data: bytes) -> str:
    return base64.b64encode(data).decode()
