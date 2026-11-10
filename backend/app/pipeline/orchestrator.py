"""Orchestrator contract (Phase 0: NullOrchestrator only)."""

from collections.abc import Callable
from collections.abc import Mapping
from typing import Any
from typing import Protocol

from backend.app.adapters.base import Verifier
from backend.app.core.policy import Policy
from backend.app.domain.enums import RunMode
from backend.app.domain.submission import VendorSubmission


class RunEvent(dict[str, Any]):  # lightweight; real RunEvent lives in api/events.py
    pass


class CheckCache(Protocol):
    def get(self, fp: str) -> Any: ...
    def put(self, fp: str, findings: Any) -> None: ...


class LLMClient(Protocol):
    async def structured(self, **kwargs: Any) -> Any: ...


class Clock(Protocol):
    def now(self) -> Any: ...


class RunContext:
    def __init__(
        self,
        case_id: str,
        run_id: str,
        submission: VendorSubmission,
        policy: Policy,
        adapters: Mapping[str, Verifier[Any, Any]],
        llm: LLMClient,
        clock: Clock,
        cache: CheckCache,
        emit: Callable[[RunEvent], None],
    ) -> None:
        self.case_id = case_id
        self.run_id = run_id
        self.submission = submission
        self.policy = policy
        self.adapters = adapters
        self.llm = llm
        self.clock = clock
        self.cache = cache
        self.emit = emit

    def value(self, path: str) -> Any:
        return None


class Orchestrator(Protocol):
    async def run(self, ctx: RunContext, mode: RunMode) -> None: ...


class NullOrchestrator:
    """Phase 0 skeleton: emits run lifecycle + one noop check."""

    async def run(self, ctx: RunContext, mode: RunMode) -> None:
        ctx.emit(RunEvent({"type": "run.started", "run_id": ctx.run_id}))
        ctx.emit(RunEvent({"type": "check.completed", "check_id": "NOOP"}))
        ctx.emit(RunEvent({"type": "decision.made", "status": "APPROVED"}))
        ctx.emit(RunEvent({"type": "run.completed", "run_id": ctx.run_id}))
