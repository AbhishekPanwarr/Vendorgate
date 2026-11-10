import asyncio

import pytest

from backend.app.llm.tasks_other import PolishResult


class _Tool:
    def __init__(self, payload):
        self.type = "tool_use"
        self.input = payload


class _Msg:
    def __init__(self, tools):
        self.content = tools


class _Messages:
    def __init__(self, payloads):
        self.payloads = payloads
        self.n = 0

    async def create(self, **kw):
        p = self.payloads[min(self.n, len(self.payloads) - 1)]
        self.n += 1
        return _Msg([_Tool(p)])


def _provider(payloads):
    from backend.app.llm import provider_claude as pc

    p = pc.ClaudeProvider.__new__(pc.ClaudeProvider)
    p.api_key = "test"
    p._client = type("C", (), {"messages": _Messages(payloads)})()
    return p


def test_claude_success():
    p = _provider([{"body": "hi [[X]]"}])
    out = asyncio.run(p.structured(task="t", model="m", system="s", user="u", schema=PolishResult))
    assert out.body == "hi [[X]]"


def test_claude_no_key(monkeypatch):
    from backend.app.llm import provider_claude as pc

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError):
        pc.ClaudeProvider(api_key="")
