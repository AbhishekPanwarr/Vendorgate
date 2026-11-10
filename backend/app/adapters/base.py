"""Verifier protocol."""

from datetime import datetime
from enum import StrEnum
from typing import Generic
from typing import Protocol
from typing import TypeVar
from typing import runtime_checkable

from pydantic import BaseModel


class VerifierStatus(StrEnum):
    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    MISMATCH = "MISMATCH"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"


T = TypeVar("T")


class VerifierResult(BaseModel, Generic[T]):
    status: VerifierStatus
    data: T | None = None
    source: str
    adapter_version: str
    retrieved_at: datetime
    latency_ms: int
    call_id: str
    fixture_id: str | None = None


Req = TypeVar("Req", contravariant=True)
Resp = TypeVar("Resp", covariant=True)


@runtime_checkable
class Verifier(Protocol[Req, Resp]):  # type: ignore[misc]  # generic Verifier Protocol; mypy can't infer variance across the two TypeVars. Do not remove — see ADR 0006.
    name: str
    version: str

    async def verify(self, req: Req, *, timeout: float) -> VerifierResult[Resp]: ...


class AdapterUnavailable(RuntimeError):
    """Raised for ERROR/TIMEOUT/RATE_LIMITED; caught by orchestrator."""
