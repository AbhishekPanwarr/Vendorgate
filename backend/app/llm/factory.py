"""LLM factory: mode from env, replay store from committed fixtures."""

import os
from typing import Any


def make_llm(store: dict[str, Any] | None = None) -> Any:
    from backend.app.llm.client import CachingLLM

    mode = os.environ.get("LLM_MODE", "replay")
    if store is None:
        try:
            from backend.tests.fixtures.llm_cache_helper import load_cache

            store = load_cache()
        except Exception:
            store = {}
    inner = None
    if mode in ("live", "record"):
        from backend.app.llm.provider_meta import MetaProvider

        inner = MetaProvider()
    return CachingLLM(
        inner, mode, store, budget_tokens=int(os.environ.get("LLM_BUDGET_TOKENS", "20000"))
    )


def llm_model(fast: bool = True) -> str:
    return os.environ.get("LLM_MODEL_FAST" if fast else "LLM_MODEL_STRONG", "muse-spark-1.3")
