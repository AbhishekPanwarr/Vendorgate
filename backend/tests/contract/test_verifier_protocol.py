import asyncio
from datetime import datetime
from datetime import timezone

from backend.app.adapters.base import AdapterUnavailable
from backend.app.adapters.base import Verifier
from backend.app.adapters.base import VerifierResult
from backend.app.adapters.base import VerifierStatus
from backend.app.adapters.mocks.noop import NoopVerifier


def test_runtime_checkable():
    assert isinstance(NoopVerifier(), Verifier)


def test_noop_roundtrip():
    r = asyncio.run(NoopVerifier().verify({}, timeout=1.0))
    assert isinstance(r, VerifierResult)
    assert r.call_id and r.retrieved_at


def test_result_requires_fields():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VerifierResult(
            status=VerifierStatus.OK, source="x", adapter_version="v", latency_ms=0
        )  # missing call_id/retrieved_at
    assert issubclass(AdapterUnavailable, RuntimeError)
    assert datetime.now(timezone.utc) is not None
