"""SQLAlchemy models (all B 8.4 tables, Postgres-compatible)."""

import uuid
from datetime import datetime
from datetime import timezone

from sqlalchemy import DateTime
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from typing import Any

from sqlalchemy.orm import mapped_column


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    vendor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="NEW")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    awaiting: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tier: Mapped[str] = mapped_column(String(32), default="LOW")
    score: Mapped[float] = mapped_column(default=0.0)
    attempt_count: Mapped[int] = mapped_column(default=0)
    payments_blocked: Mapped[bool] = mapped_column(default=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")


class SubmissionVersion(Base):
    __tablename__ = "submission_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[str] = mapped_column(String(64), default="system")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    submission_version_id: Mapped[str] = mapped_column(String(64))
    doc_type: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(256))
    sha256: Mapped[str] = mapped_column(String(128))
    path: Mapped[str] = mapped_column(String(512), default="")
    pages: Mapped[int] = mapped_column(default=1)
    text_layer: Mapped[bool] = mapped_column(default=True)
    extracted: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    submission_version_id: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16), default="FULL")
    policy_version: Mapped[str] = mapped_column(String(128), default="")
    llm_mode: Mapped[str] = mapped_column(String(16), default="replay")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cache_hits: Mapped[int] = mapped_column(default=0)
    cache_misses: Mapped[int] = mapped_column(default=0)
    llm_tokens: Mapped[int] = mapped_column(default=0)
    llm_cost_usd: Mapped[float] = mapped_column(default=0.0)


class ClaimRow(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    run_id: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(256))
    raw: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    value: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    doc_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page: Mapped[int | None] = mapped_column(nullable=True)
    quote: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    confidence: Mapped[float] = mapped_column(default=1.0)


class FindingRow(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    run_id: Mapped[str] = mapped_column(String(64))
    check_id: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(16))
    outcome: Mapped[str] = mapped_column(String(32))
    severity: Mapped[int] = mapped_column(default=0)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fixed_by: Mapped[str] = mapped_column(String(32), default="NONE")
    deterministic: Mapped[bool] = mapped_column(default=True)
    cached: Mapped[bool] = mapped_column(default=False)
    fingerprint: Mapped[str] = mapped_column(String(128), default="")
    body: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class DecisionRow(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    run_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    awaiting: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tier: Mapped[str] = mapped_column(String(32))
    score_total: Mapped[float] = mapped_column(default=0.0)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason_codes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    counterfactuals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reproducibility_hash: Mapped[str] = mapped_column(String(128), default="")


class CheckCacheRow(Base):
    __tablename__ = "check_cache"
    fingerprint: Mapped[str] = mapped_column(String(128), primary_key=True)
    check_id: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    seq: Mapped[int] = mapped_column(default=0)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(128), default="GENESIS")
    entry_hash: Mapped[str] = mapped_column(String(128), default="")


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(String(2048), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResolutionRow(Base):
    __tablename__ = "resolutions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    finding_key: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(String(2048))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Callback(Base):
    __tablename__ = "callbacks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    number_used: Mapped[str] = mapped_column(String(64))
    number_source: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(64), default="")
    independent: Mapped[bool] = mapped_column(default=False)
    actor: Mapped[str] = mapped_column(String(64), default="")
    attested: Mapped[bool] = mapped_column(default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LlmCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    run_id: Mapped[str] = mapped_column(String(64))
    task: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_hash: Mapped[str] = mapped_column(String(128))
    in_tokens: Mapped[int] = mapped_column(default=0)
    out_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    cache_hit: Mapped[bool] = mapped_column(default=False)
    cost_usd: Mapped[float] = mapped_column(default=0.0)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    case_id: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[str] = mapped_column(String(64))
    audience: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(String(8192))
    items: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    legal_name: Mapped[str] = mapped_column(String(512))
    name_core: Mapped[str] = mapped_column(String(512), default="")
    tax_id_norm: Mapped[str] = mapped_column(String(128), default="")
    country: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    risk_tier: Mapped[str] = mapped_column(String(32), default="LOW")
    created_from_case: Mapped[str] = mapped_column(String(64), default="")
    attrs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class VendorBankAccount(Base):
    __tablename__ = "vendor_bank_accounts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    vendor_id: Mapped[str] = mapped_column(String(64))
    acct_hash: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(8))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str] = mapped_column(String(64), default="")
    active: Mapped[bool] = mapped_column(default=True)


class ErpOutbox(Base):
    __tablename__ = "erp_outbox"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    vendor_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    delivered: Mapped[bool] = mapped_column(default=False)


class EvalRun(Base):
    __tablename__ = "eval_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    mode: Mapped[str] = mapped_column(String(32))
    split: Mapped[str] = mapped_column(String(32))
    seed: Mapped[int] = mapped_column(default=0)
    dataset_hash: Mapped[str] = mapped_column(String(128), default="")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class EvalCaseResult(Base):
    __tablename__ = "eval_case_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    eval_run_id: Mapped[str] = mapped_column(String(64))
    case_id: Mapped[str] = mapped_column(String(64))
    expected: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actual: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correct: Mapped[bool] = mapped_column(default=False)
    latency_ms: Mapped[int] = mapped_column(default=0)


class ClockState(Base):
    __tablename__ = "clock_state"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="clock")
    virtual_now: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AdapterFault(Base):
    __tablename__ = "adapter_faults"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uid)
    adapter: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32))
    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
