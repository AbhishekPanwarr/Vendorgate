"""LLM client: protocol, caching, modes, budget, circuit breaker."""

import time
from typing import Any
from typing import Protocol

from pydantic import BaseModel

from backend.app.core.hashing import canonical_json
from backend.app.core.hashing import sha256_hex


class LLMDisabledError(RuntimeError):
    pass


class ReplayMiss(KeyError):
    pass


class LLMBudgetExceeded(RuntimeError):
    pass


class LLMClient(Protocol):
    async def structured(
        self,
        *,
        task: str,
        model: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        max_tokens: int = 1024,
    ) -> BaseModel: ...


def cache_key(model: str, system: str, user: str, schema: type[BaseModel]) -> str:
    return sha256_hex(
        canonical_json(
            {"model": model, "system": system, "user": user, "schema": schema.model_json_schema()}
        )
    )


class CachingLLM:
    def __init__(
        self, inner: Any, mode: str, store: dict[str, Any], budget_tokens: int = 20000
    ) -> None:
        assert mode in ("live", "record", "replay", "off")
        self.inner = inner
        self.mode = mode
        self.store = store
        self.spent = 0
        self.budget = budget_tokens
        self.failures = 0
        self.breaker_open_until = 0.0

    async def structured(self, **kw: Any) -> BaseModel:
        if self.mode == "off":
            raise LLMDisabledError("LLM is off")
        if self.spent >= self.budget:
            raise LLMBudgetExceeded("llm_budget_exceeded")
        schema = kw["schema"]
        key = cache_key(kw["model"], kw["system"], kw["user"], schema)
        if self.mode in ("replay", "record") and key in self.store:
            validated = schema.model_validate(self.store[key])
            assert isinstance(validated, BaseModel)
            return validated
        if self.mode == "replay":
            raise ReplayMiss(key)
        if time.time() < self.breaker_open_until:
            raise LLMDisabledError("circuit open")
        try:
            out = await self.inner.structured(**kw)
        except Exception:
            self.failures += 1
            if self.failures >= 3:
                self.breaker_open_until = time.time() + 30
            raise
        self.failures = 0
        used = int(getattr(out, "_tokens_used", 500))
        self.spent += used
        if self.mode in ("record", "live"):
            data = out.model_dump()
            data["_tokens_used"] = used
            self.store[key] = data
        assert isinstance(out, BaseModel)
        return out
