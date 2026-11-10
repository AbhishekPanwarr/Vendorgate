import asyncio

from backend.app.pipeline.orchestrator import NullOrchestrator
from backend.app.pipeline.orchestrator import RunContext
from backend.app.domain.enums import RunMode


class _LLM:
    async def structured(self, **kw):  # noqa: ANN003
        raise NotImplementedError


class _Clock:
    def now(self):  # noqa: ANN202
        return None


class _Cache:
    def get(self, fp):  # noqa: ANN001, ANN202
        return None

    def put(self, fp, findings):  # noqa: ANN001, ANN202
        pass


def _ctx():
    from backend.app.core.policy import load_policy
    from backend.app.domain.submission import VendorSubmission

    sub = VendorSubmission.model_construct()
    return RunContext(
        case_id="c",
        run_id="r",
        submission=sub,
        policy=load_policy("policy"),
        adapters={},
        llm=_LLM(),
        clock=_Clock(),
        cache=_Cache(),
        emit=lambda e: events.append(dict(e)),
    )


events: list = []


def test_null_orchestrator_emits():
    global events
    events = []
    asyncio.run(NullOrchestrator().run(_ctx(), RunMode.FULL))
    types = [e["type"] for e in events]
    assert types == ["run.started", "check.completed", "decision.made", "run.completed"]
