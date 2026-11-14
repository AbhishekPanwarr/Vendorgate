from backend.app.adapters.faults import CircuitBreaker
from backend.app.adapters.faults import clear_faults
from backend.app.adapters.faults import guarded_call
from backend.app.adapters.faults import set_fault


def test_fault_modes():
    import anyio

    from backend.app.adapters.base import AdapterUnavailable
    from backend.app.adapters.base import VerifierResult
    from backend.app.adapters.base import VerifierStatus

    async def ok():
        from datetime import datetime, timezone

        return VerifierResult(
            status=VerifierStatus.OK,
            source="t",
            adapter_version="0.1.0",
            retrieved_at=datetime.now(timezone.utc),
            latency_ms=1,
            call_id="c1",
        )

    clear_faults()
    assert anyio.run(guarded_call, "irs", ok).status == VerifierStatus.OK
    set_fault("irs", "TIMEOUT")
    try:
        anyio.run(guarded_call, "irs", ok)
        raise AssertionError("should raise")
    except AdapterUnavailable:
        pass
    set_fault("irs", "ERROR")
    try:
        anyio.run(guarded_call, "irs", ok)
        raise AssertionError("should raise")
    except AdapterUnavailable:
        pass
    clear_faults()


def test_circuit_opens_and_half_opens():
    class FakeClock:
        def __init__(self):
            self.t = 1000.0

        def time(self):
            return self.t

    from backend.app.adapters.faults import _BREAKERS

    _BREAKERS.pop("x", None)
    clock = FakeClock()
    br = CircuitBreaker(clock=clock)
    _BREAKERS["x"] = br
    for _ in range(3):
        br.record_failure()
    assert br.is_open
    clock.t += 31
    assert not br.is_open
    _BREAKERS.pop("x", None)


def test_schema_parses_sample():
    import json

    from backend.app.adapters.mocks._schema import MockFixture

    with open("backend/app/adapters/mocks/fixtures/sample.jsonl") as fh:
        row = json.loads(fh.readline())
    fx = MockFixture.model_validate(row)
    assert fx.fixture_id == "sample-1"


def test_slow_and_half_open_retry():
    import anyio

    from backend.app.adapters.faults import _BREAKERS
    from backend.app.adapters.faults import breaker_for

    _BREAKERS.pop("slow-ad", None)
    set_fault("slow-ad", "SLOW")
    import functools
    import time

    try:
        t0 = time.time()
        # SLOW injects latency past the budget but still succeeds
        res = anyio.run(functools.partial(guarded_call, "slow-ad", _ok_fn(), timeout=0.05))
        assert res.status.value == "OK"
        assert time.time() - t0 >= 0.05
    finally:
        clear_faults()
        _BREAKERS.pop("slow-ad", None)
    assert not breaker_for("slow-ad").is_open


def _ok_fn():
    from datetime import datetime, timezone

    from backend.app.adapters.base import VerifierResult
    from backend.app.adapters.base import VerifierStatus

    async def ok():
        return VerifierResult(
            status=VerifierStatus.OK,
            source="t",
            adapter_version="0.1.0",
            retrieved_at=datetime.now(timezone.utc),
            latency_ms=1,
            call_id="c1",
        )

    return ok
