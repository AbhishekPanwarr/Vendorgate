"""Mock fixture schema."""

from pydantic import BaseModel

from typing import Any

from backend.app.adapters.base import VerifierResult


class MockFixture(BaseModel):
    fixture_id: str
    adapter: str
    version: str
    request_hash: str
    response: VerifierResult[Any]
