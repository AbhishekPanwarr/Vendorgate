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


STAGE_LAYERS: list[list[str]] = [
    ["S0"],
    ["S1", "S6", "S7"],
    ["S2", "S3"],
    ["S4"],
    ["S5"],
    ["S8"],
    ["S9"],
    ["S10"],
    ["S11"],
    ["S12"],
]


class DagOrchestrator:
    """Phase 1: runs registered checks layer by layer (anyio task groups)."""

    async def run(self, ctx: Any, mode: RunMode) -> None:
        import anyio

        from backend.app.pipeline import registry

        ctx.emit({"type": "run.started", "run_id": ctx.run_id})
        for layer in STAGE_LAYERS:
            specs = [s for s in registry.all_specs() if s.stage in layer]
            if not specs:
                continue
            ctx.emit({"type": "stage.started", "stages": layer})
            async with anyio.create_task_group() as tg:
                for spec in specs:
                    tg.start_soon(self._run_check, ctx, spec)
            ctx.emit({"type": "stage.completed", "stages": layer})
        ctx.emit({"type": "run.completed", "run_id": ctx.run_id})

    async def _run_check(self, ctx: Any, spec: Any) -> None:
        import time

        import anyio

        from backend.app.adapters.base import AdapterUnavailable
        from backend.app.core.hashing import fingerprint
        from backend.app.domain.enums import Outcome
        from backend.app.domain.enums import Severity
        from backend.app.domain.models import Evidence
        from backend.app.domain.models import Finding

        reads = {p: ctx.value(p) for p in spec.reads}
        # Fault state participates in the fingerprint: a cached PASS must
        # never be served while its adapter is faulted (fail-closed).
        from backend.app.adapters import faults as _faults

        fault_state = {f"fault:{a}": _faults.FAULTS.get(a, "OK") for a in spec.adapters}
        fp = fingerprint(
            check_id=spec.id,
            version=spec.version,
            subject=None,
            policy_hash=ctx.policy.hash_for(spec.id),
            reads=reads,
            adapters={a: getattr(ctx.adapters.get(a), "version", "?") for a in spec.adapters},
            lists=fault_state,
        )
        if (hit := ctx.cache.get(fp)) is not None and spec.stage != "S10":
            # S10 checks read other findings (e.g. C-POL-02 reads C-DUP-05),
            # which fingerprints cannot capture: always re-run S10.
            for f in hit:
                ctx.findings.append(f.model_copy(update={"cached": True}))
                ctx.emit(
                    {
                        "type": "check.completed",
                        "check_id": spec.id,
                        "cached": True,
                        "findings": [f.model_dump(mode="json") for f in hit],
                    }
                )
            return
        ctx.emit({"type": "check.started", "check_id": spec.id})
        t0 = time.time()
        try:
            with anyio.fail_after(spec.timeout_s):
                findings = await spec.fn(ctx)
        except TimeoutError:
            findings = [
                self._unverifiable(spec, "CHECK_TIMEOUT", Finding, Evidence, Outcome, Severity)
            ]
        except AdapterUnavailable as e:
            findings = [
                self._unverifiable(
                    spec, f"VERIFIER_UNAVAILABLE: {e}", Finding, Evidence, Outcome, Severity
                )
            ]
        except Exception:  # noqa: BLE001 — a bug must never crash a run
            import structlog

            structlog.get_logger().exception("check_failed", check=spec.id)
            findings = [
                self._unverifiable(
                    spec, "CHECK_INTERNAL_ERROR", Finding, Evidence, Outcome, Severity
                )
            ]
        ms = int((time.time() - t0) * 1000)
        for f in findings:
            f.duration_ms = ms
            if not f.fingerprint:
                f.fingerprint = fp
            self._validate(f)
        if all(f.outcome != Outcome.UNVERIFIABLE for f in findings):
            ctx.cache.put(fp, findings)
        ctx.findings.extend(findings)
        ctx.emit(
            {
                "type": "check.completed",
                "check_id": spec.id,
                "findings": [f.model_dump(mode="json") for f in findings],
            }
        )

    @staticmethod
    def _unverifiable(
        spec: Any, detail: str, Finding: Any, Evidence: Any, Outcome: Any, Severity: Any
    ) -> Any:
        return Finding(
            check_id=spec.id,
            stage=spec.stage,
            check_version=spec.version,
            outcome=Outcome.UNVERIFIABLE,
            severity=Severity.HARD,
            reason_code="VERIFIER_UNAVAILABLE",
            title=f"{spec.id} unverifiable",
            detail=detail,
            evidence=[Evidence(kind="rule", ref=spec.id, summary=detail)],
            fixed_by="INTERNAL",
            mandatory=spec.mandatory,
            deterministic=True,
            reads=list(spec.reads),
        )

    @staticmethod
    def _validate(f: Any) -> None:
        if f.outcome in ("FAIL", "WARN", "UNVERIFIABLE") and not f.evidence:
            raise ValueError(f"{f.check_id}: evidence required")
        if str(f.outcome) == "FAIL" and not f.reason_code:
            raise ValueError(f"{f.check_id}: reason_code required")
