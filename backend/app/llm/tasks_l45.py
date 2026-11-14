"""L4 polish + L5 brief runners (best-effort; template/omit on miss)."""

from typing import Any

from backend.app.llm.tasks_other import ApproverBrief
from backend.app.llm.tasks_other import L4_SYSTEM
from backend.app.llm.tasks_other import L5_SYSTEM
from backend.app.llm.tasks_other import PolishResult


async def polish_message(
    llm: Any, model: str, subject: str, body: str, items: list[dict[str, Any]]
) -> dict[str, Any]:
    from backend.app.comms.messages import check_message

    anchors = "\n".join(f"[[{it['fix_code']}]]" for it in items)
    try:
        out = await llm.structured(
            task="polish message",
            model=model,
            system=L4_SYSTEM,
            user=f"Subject: {subject}\n\n{body}\n\nItems:\n{anchors}",
            schema=PolishResult,
            max_tokens=2048,
        )
        assert isinstance(out, PolishResult)
        errs = check_message(subject, out.body, [{"fix_code": it["fix_code"]} for it in items])
        if errs:
            return {"body": body, "polished": False, "errors": errs}
        return {"body": out.body, "polished": True, "errors": []}
    except Exception as e:
        return {"body": body, "polished": False, "errors": [f"polish-fallback: {e}"]}


async def approver_brief(
    llm: Any, model: str, finding_ids: list[str], notes: list[str]
) -> dict[str, Any]:
    try:
        out = await llm.structured(
            task="approver brief",
            model=model,
            system=L5_SYSTEM,
            user="Findings:\n"
            + "\n".join(f"- {fid}: {note}" for fid, note in zip(finding_ids, notes)),
            schema=ApproverBrief,
            max_tokens=2048,
        )
        assert isinstance(out, ApproverBrief)
        import re

        cited = set(re.findall(r"\(F-(\d+)\)", out.summary))
        valid = {str(i + 1) for i in range(len(finding_ids))}
        if not cited <= valid:
            return {"summary": "", "omitted": True}
        return {"summary": out.summary, "omitted": False}
    except Exception:
        return {"summary": "", "omitted": True}
