"""Reads audit: every claim path a check touches must be in its reads[]."""

import asyncio
import json
import re

from backend.app.core.policy import load_policy
from backend.app.pipeline import registry


def _ctx():
    import backend.app.pipeline.checks.bank  # noqa: F401
    import backend.app.pipeline.checks.doc  # noqa: F401
    import backend.app.pipeline.checks.dup  # noqa: F401
    import backend.app.pipeline.checks.geo  # noqa: F401
    import backend.app.pipeline.checks.name  # noqa: F401
    import backend.app.pipeline.checks.req  # noqa: F401
    import backend.app.pipeline.checks.san  # noqa: F401
    import backend.app.pipeline.checks.tax  # noqa: F401
    import backend.app.pipeline.checks.ver  # noqa: F401
    from backend.app.core.clock import RealClock
    from backend.app.domain.submission import VendorSubmission
    from backend.app.network.graph import seed_master
    from backend.app.pipeline.context import CheckCache
    from backend.app.pipeline.context import RunContext
    from backend.app.pipeline.stages.s0_intake import build_claims

    seed_master()
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        sub = VendorSubmission.model_validate(json.load(fh))
    accessed: list[str] = []
    ctx = RunContext(
        case_id="c",
        run_id="r",
        submission=sub,
        policy=load_policy("policy"),
        adapters={},
        llm=None,
        clock=RealClock(),
        cache=CheckCache(),
        emit=lambda e: None,
    )
    for cl in build_claims(sub):
        ctx.add_claim(cl)
    orig_value = ctx.value

    def logging_value(path):
        accessed.append(path)
        return orig_value(path)

    ctx.value = logging_value  # type: ignore[method-assign]
    return ctx, accessed


def test_all_checks_declare_reads():
    import backend.app.pipeline.checks.bank  # noqa: F401
    import backend.app.pipeline.checks.doc  # noqa: F401
    import backend.app.pipeline.checks.dup  # noqa: F401
    import backend.app.pipeline.checks.geo  # noqa: F401
    import backend.app.pipeline.checks.name  # noqa: F401
    import backend.app.pipeline.checks.req  # noqa: F401
    import backend.app.pipeline.checks.san  # noqa: F401
    import backend.app.pipeline.checks.tax  # noqa: F401
    import backend.app.pipeline.checks.ver  # noqa: F401

    bad = []
    for spec in registry.all_specs():
        if spec.stage == "S10":
            continue  # reads other findings by design (never cached)
        ctx, accessed = _ctx()
        try:
            asyncio.run(spec.fn(ctx))
        except Exception:
            pass  # errors are fail-closed at runtime; audit is about reads
        declared = set(spec.reads)
        for p in set(accessed):
            if p not in declared and not (
                # indexed document paths are covered by the digest claim
                re.match(r"documents\.\d+\.", p) and "documents.digest" in declared
            ):
                bad.append((spec.id, p))
    assert bad == [], f"undeclared reads: {bad}"
