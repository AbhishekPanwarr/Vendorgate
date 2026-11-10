"""Noop verifier (Phase 0 skeleton)."""

from datetime import datetime
from datetime import timezone

from typing import Any

from backend.app.adapters.base import VerifierResult
from backend.app.adapters.base import VerifierStatus


class NoopVerifier:
    name = "noop"
    version = "0.0.0"

    async def verify(self, req: object, *, timeout: float) -> VerifierResult[Any]:
        return VerifierResult(
            status=VerifierStatus.OK,
            data=None,
            source="noop",
            adapter_version=self.version,
            retrieved_at=datetime.now(timezone.utc),
            latency_ms=0,
            call_id="noop-1",
            fixture_id=None,
        )
