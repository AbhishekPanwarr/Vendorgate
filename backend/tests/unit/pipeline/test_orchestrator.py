import anyio
import pytest

from backend.app.core.clock import RealClock
from backend.app.core.policy import load_policy
from backend.app.domain.enums import RunMode
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.domain.enums import Outcome
from backend.app.pipeline import registry
from backend.app.pipeline.context import CheckCache
from backend.app.pipeline.context import RunContext
from backend.app.pipeline.orchestrator import DagOrchestrator
from backend.app.pipeline.registry import check


@pytest.fixture(autouse=True)
def _isolated_registry():
    import backend.app.pipeline.checks.bank  # noqa: F401
    import backend.app.pipeline.checks.geo  # noqa: F401
    import backend.app.pipeline.checks.name  # noqa: F401
    import backend.app.pipeline.checks.req  # noqa: F401
    import backend.app.pipeline.checks.tax  # noqa: F401

    saved = dict(registry._registry)
    registry.clear()
    yield
    registry.clear()
    registry._registry.update(saved)


def _ctx():
    from backend.app.domain.submission import VendorSubmission

    events: list = []
    return RunContext(
        case_id="c",
        run_id="r",
        submission=VendorSubmission.model_construct(),
        policy=load_policy("policy"),
        adapters={},
        llm=None,
        clock=RealClock(),
        cache=CheckCache(),
        emit=lambda e: events.append(e),
    ), events


def test_check_exception_becomes_unverifiable():
    @check(id="C-BOOM", stage="S3", version=1, mandatory=True, reads=())
    async def _boom(ctx):  # noqa: ANN001
        raise RuntimeError("bug")

    ctx, _ = _ctx()
    anyio.run(DagOrchestrator().run, ctx, RunMode.FULL)
    f = [x for x in ctx.findings if x.check_id == "C-BOOM"][0]
    assert f.outcome == Outcome.UNVERIFIABLE


def test_cache_hit_second_run():
    calls = {"n": 0}

    @check(id="C-CNT", stage="S3", version=1, mandatory=True, reads=())
    async def _cnt(ctx):  # noqa: ANN001
        calls["n"] += 1
        return [
            Finding(
                check_id="C-CNT",
                stage="S3",
                check_version=1,
                outcome=Outcome.PASS,
                title="t",
                detail="d",
                evidence=[Evidence(kind="rule", ref="C-CNT", summary="ok")],
            )
        ]

    ctx, events = _ctx()
    anyio.run(DagOrchestrator().run, ctx, RunMode.FULL)
    assert calls["n"] == 1
    # second run shares cache
    from backend.app.domain.submission import VendorSubmission

    ctx2 = RunContext(
        case_id="c",
        run_id="r2",
        submission=VendorSubmission.model_construct(),
        policy=ctx.policy,
        adapters={},
        llm=None,
        clock=ctx.clock,
        cache=ctx.cache,
        emit=lambda e: events.append(e),
    )
    anyio.run(DagOrchestrator().run, ctx2, RunMode.FULL)
    assert calls["n"] == 1
    assert any(f.cached for f in ctx2.findings)
