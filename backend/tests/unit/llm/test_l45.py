import asyncio

from backend.app.llm.client import CachingLLM
from backend.app.llm.tasks_l45 import approver_brief
from backend.app.llm.tasks_l45 import polish_message
from backend.tests.fixtures.llm_cache_helper import load_cache


def _llm():
    return CachingLLM(None, "replay", load_cache())


def test_polish_keeps_anchors():
    llm = _llm()
    body = (
        "Hi, thanks for submitting details for Acme Trading Co.\n"
        "Please fix the following items:\n"
        "1. [[UPLOAD_DBA_PROOF]] Confirm your legal entity name.: "
        "They look like the same business but we need proof.\n"
        "Please resubmit by in 14 days. [Resubmit → /resubmit]"
    )
    items = [{"fix_code": "UPLOAD_DBA_PROOF"}]
    r = asyncio.run(polish_message(llm, "muse-spark-1.3", "Acme — action needed", body, items))
    assert r["polished"] is True
    assert "[[UPLOAD_DBA_PROOF]]" in r["body"]


def test_polish_fallback_on_miss():
    from backend.app.llm.client import CachingLLM as C

    llm = C(None, "replay", {})
    r = asyncio.run(polish_message(llm, "muse-spark-1.3", "s", "body [[X]]", [{"fix_code": "X"}]))
    assert r["polished"] is False and r["body"] == "body [[X]]"


def test_brief_cites_only_known_ids():
    llm = _llm()
    r = asyncio.run(
        approver_brief(
            llm,
            "muse-spark-1.3",
            ["F-1", "F-2"],
            ["Name ↔ bank holder (LEGAL_FORM_UNCONFIRMED)", "Bank ownership verified"],
        )
    )
    assert r["omitted"] is False
    assert "(F-1)" in r["summary"] and "(F-9)" not in r["summary"]


def test_brief_hallucinated_id_omitted():
    from backend.app.llm.client import CachingLLM as C

    llm = C(None, "replay", {})
    r = asyncio.run(approver_brief(llm, "muse-spark-1.3", ["F-1"], ["x"]))
    assert r["omitted"] is True
