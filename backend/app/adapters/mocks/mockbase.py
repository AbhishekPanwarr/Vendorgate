"""Mock verifier base: JSONL fixtures keyed by stable business key."""

import json
import uuid
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from backend.app.adapters.base import VerifierResult
from backend.app.adapters.base import VerifierStatus
from backend.app.adapters.faults import guarded_call

_FIX_DIR = Path(__file__).parent / "fixtures"

# Per-case overlay for eval/fool-it: {(adapter_name, key): row}. Checked first.
_OVERLAY: dict[tuple[str, str], dict[str, Any]] = {}


class MockVerifier:
    name = "mock"
    version = "0.1.0"
    fixture_file = ""
    key_field = ""

    def _rows(self) -> dict[str, dict[str, Any]]:
        path = _FIX_DIR / self.fixture_file
        rows: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    rows[str(row["key"])] = row
        return rows

    async def verify(self, req: dict[str, Any], *, timeout: float = 5.0) -> VerifierResult[Any]:
        async def _do() -> VerifierResult[Any]:
            key = str(req.get(self.key_field, ""))
            row = _OVERLAY.get((self.name, key))
            if row is None:
                rows = self._rows()
                row = rows.get(key)
            if row is None:
                return VerifierResult(
                    status=VerifierStatus.NOT_FOUND,
                    data=None,
                    source=self.name,
                    adapter_version=self.version,
                    retrieved_at=datetime.now(timezone.utc),
                    latency_ms=1,
                    call_id=uuid.uuid4().hex[:12],
                    fixture_id=None,
                )
            data = row.get("data")
            status = VerifierStatus(row.get("status", "OK"))
            return VerifierResult(
                status=status,
                data=data,
                source=self.name,
                adapter_version=self.version,
                retrieved_at=datetime.now(timezone.utc),
                latency_ms=1,
                call_id=uuid.uuid4().hex[:12],
                fixture_id=row.get("fixture_id"),
            )

        return await guarded_call(self.name, _do, timeout=timeout)
