from backend.app.llm.provider_meta import MetaProvider
from backend.app.llm.provider_meta import _extract_json
from backend.app.llm.provider_meta import required_models
from backend.app.llm.tasks_other import PolishResult


class _Msg:
    def __init__(self, content, usage=None):
        self.content = content
        self.usage = usage


class _Usage:
    def __init__(self, pin=10, pout=20):
        self.input_tokens = pin
        self.output_tokens = pout


class _Completions:
    def __init__(self, texts):
        self.texts = texts
        self.n = 0

    def create(self, **kw):
        t = self.texts[min(self.n, len(self.texts) - 1)]
        self.n += 1
        m = type("M", (), {"content": t})()
        return type("R", (), {"choices": [type("C", (), {"message": m})()], "usage": _Usage()})()


class _Client:
    def __init__(self, texts):
        self.chat = type("Chat", (), {"completions": _Completions(texts)})()


def _provider(texts):
    p = MetaProvider.__new__(MetaProvider)
    p.api_key = "test"
    p._client = _Client(texts)
    p.base_url = "https://api.meta.ai/v1"
    return p


def test_extract_json():
    assert _extract_json('prefix {"a": 1} suffix') == '{"a": 1}'
    assert _extract_json("no json") == "{}"


def test_required_models_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODEL_FAST", raising=False)
    monkeypatch.delenv("LLM_MODEL_STRONG", raising=False)
    assert required_models() == ("muse-spark-1.3", "muse-spark-1.3")


def test_provider_no_key(monkeypatch):
    import pytest

    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(ValueError):
        MetaProvider(api_key="")


def test_structured_success():
    import asyncio

    p = _provider(['{"body": "hello [[X]]"}'])
    out = asyncio.run(p.structured(task="t", model="m", system="s", user="u", schema=PolishResult))
    assert out.body == "hello [[X]]"


def test_structured_retry_then_ok():
    import asyncio

    p = _provider(["not json", '{"body": "ok [[X]]"}'])
    out = asyncio.run(p.structured(task="t", model="m", system="s", user="u", schema=PolishResult))
    assert out.body == "ok [[X]]"


def test_structured_fails_twice():
    import asyncio

    import pytest

    p = _provider(["nope", "still nope"])
    with pytest.raises(Exception):
        asyncio.run(p.structured(task="t", model="m", system="s", user="u", schema=PolishResult))
