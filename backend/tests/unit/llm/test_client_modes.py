import asyncio

from backend.app.llm.client import CachingLLM
from backend.app.llm.tasks_other import PolishResult


def test_record_and_breaker():
    store: dict = {}
    llm = CachingLLM(_Echo(), "record", store, budget_tokens=100000)
    out = asyncio.run(
        llm.structured(task="t", model="m", system="s", user="u1", schema=PolishResult)
    )
    assert out.body == "echo:u1"
    assert len(store) == 1
    # replay serves without inner
    llm2 = CachingLLM(None, "replay", store)
    out2 = asyncio.run(
        llm2.structured(task="t", model="m", system="s", user="u1", schema=PolishResult)
    )
    assert out2.body == "echo:u1"


def test_breaker_opens_after_3():
    llm = CachingLLM(_Fail(), "live", {})
    for _ in range(3):
        try:
            asyncio.run(
                llm.structured(task="t", model="m", system="s", user="u", schema=PolishResult)
            )
        except Exception:
            pass
    import pytest

    from backend.app.llm.client import LLMDisabledError

    with pytest.raises(LLMDisabledError):
        asyncio.run(llm.structured(task="t", model="m", system="s", user="u", schema=PolishResult))


class _Echo:
    async def structured(self, **kw):
        from backend.app.llm.tasks_other import PolishResult as P

        out = P(body="echo:" + kw["user"])
        out._tokens_used = 10
        return out


class _Fail:
    async def structured(self, **kw):
        raise ValueError("boom")


def test_factory_modes(monkeypatch):
    from backend.app.llm import factory

    monkeypatch.setenv("MODEL_API_KEY", "dummy")
    monkeypatch.setenv("LLM_MODEL_FAST", "muse-spark-1.3")
    llm = factory.make_llm({})
    assert llm.mode == "replay"
    assert factory.llm_model() == "muse-spark-1.3"
    monkeypatch.setenv("LLM_MODE", "off")
    assert factory.make_llm({}).mode == "off"
