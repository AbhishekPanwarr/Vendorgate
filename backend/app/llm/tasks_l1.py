"""L1 task runner: single place that builds extraction prompts (replay-stable)."""

from typing import Any

from backend.app.llm.tasks_extract import L1_SYSTEM
from backend.app.llm.tasks_extract import SCHEMAS


def page_text(pages: list[str]) -> str:
    return "\n".join(f"[page {i + 1}]\n{p}" for i, p in enumerate(pages))


def user_text(doc_type: str, pages: list[str]) -> str:
    return f"doc_type_hint: {doc_type}\n<document>\n{page_text(pages)}\n</document>"


async def extract_doc(llm: Any, model: str, doc_type: str, pages: list[str]) -> Any:
    schema = SCHEMAS.get(doc_type)
    if schema is None:
        from backend.app.llm.tasks_extract import GenericExtraction

        schema = GenericExtraction
    return await llm.structured(
        task=f"extract {doc_type}",
        model=model,
        system=L1_SYSTEM,
        user=user_text(doc_type, pages),
        schema=schema,
        max_tokens=2048,
    )
