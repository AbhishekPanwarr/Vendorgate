import asyncio

from backend.app.llm.client import CachingLLM
from backend.app.llm.client import LLMBudgetExceeded
from backend.app.llm.client import LLMDisabledError
from backend.app.llm.client import ReplayMiss
from backend.app.llm.tasks_other import AdjudicationVerdict
from backend.tests.fixtures.llm_cache_helper import load_cache


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _replay():
    return CachingLLM(None, "replay", load_cache())


def test_cache_hit_and_miss():
    llm = _replay()
    from backend.app.ingest.text import extract_text_layer
    from backend.app.llm.tasks_extract import GSTExtraction
    from backend.app.llm.tasks_l1 import extract_doc

    pages, _ = extract_text_layer(_read("backend/tests/fixtures/pdfs/gst_hp2.pdf"))
    out = asyncio.run(extract_doc(llm, "muse-spark-1.3", "GST_CERT", pages))
    assert isinstance(out, GSTExtraction)
    assert out.gstin.value == "29AAPCA1234F1ZR"


def test_replay_miss_raises():
    import pytest

    llm = CachingLLM(None, "replay", {})
    with pytest.raises(ReplayMiss):
        asyncio.run(
            llm.structured(
                task="nope",
                model="m",
                system="s",
                user="unseen-input-xyz",
                schema=AdjudicationVerdict,
            )
        )


def test_off_and_budget():
    import pytest

    llm = CachingLLM(None, "off", {})
    with pytest.raises(LLMDisabledError):
        asyncio.run(
            llm.structured(task="t", model="m", system="s", user="u", schema=AdjudicationVerdict)
        )
    llm2 = CachingLLM(None, "replay", load_cache(), budget_tokens=0)
    with pytest.raises(LLMBudgetExceeded):
        asyncio.run(
            llm2.structured(task="t", model="m", system="s", user="u", schema=AdjudicationVerdict)
        )
