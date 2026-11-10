"""Fault injection + circuit breaker for verifier adapters."""

import asyncio
import random
import time
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from backend.app.adapters.base import AdapterUnavailable
from backend.app.adapters.base import VerifierResult
from backend.app.adapters.base import VerifierStatus

# In-memory fault table: adapter -> mode in {OK, TIMEOUT, ERROR, SLOW}.
# D-2.14 populates via tests; production reads adapter_faults rows (Phase 4+).
FAULTS: dict[str, str] = {}


def set_fault(adapter: str, mode: str) -> None:
    FAULTS[adapter] = mode


def clear_faults() -> None:
    FAULTS.clear()


class CircuitBreaker:
    def __init__(self, threshold: int = 3, half_open_s: float = 30.0, clock: Any = None) -> None:
        self.threshold = threshold
        self.half_open_s = half_open_s
        self.clock = clock or time
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if self.clock.time() - self.opened_at >= self.half_open_s:
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = self.clock.time()


_BREAKERS: dict[str, CircuitBreaker] = {}


def breaker_for(adapter: str) -> CircuitBreaker:
    return _BREAKERS.setdefault(adapter, CircuitBreaker())


async def guarded_call(
    adapter: str,
    fn: Callable[[], Awaitable["VerifierResult[Any]"]],
    timeout: float = 5.0,
    retries: int = 2,
) -> VerifierResult[Any]:
    """Run fn() with fault injection, retry, and circuit breaking."""
    br = breaker_for(adapter)
    if br.is_open:
        raise AdapterUnavailable(f"circuit open for {adapter}")
    mode = FAULTS.get(adapter, "OK")
    if mode == "SLOW":
        await asyncio.sleep(timeout + 0.1)
    if mode == "TIMEOUT":
        raise AdapterUnavailable(f"injected timeout for {adapter}")
    if mode == "ERROR":
        br.record_failure()
        raise AdapterUnavailable(f"injected error for {adapter}")
    attempt = 0
    while True:
        try:
            async with asyncio.timeout(timeout):
                result = await fn()
            br.record_success()
            return result
        except (TimeoutError, AdapterUnavailable) as e:
            status = getattr(e, "verifier_status", VerifierStatus.TIMEOUT)
            if status not in (VerifierStatus.TIMEOUT, VerifierStatus.RATE_LIMITED):
                raise
            attempt += 1
            if attempt > retries:
                br.record_failure()
                raise AdapterUnavailable(str(e)) from e
            await asyncio.sleep((2**attempt) * 0.05 + random.random() * 0.02)
