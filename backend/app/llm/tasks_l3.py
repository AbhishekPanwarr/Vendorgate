"""L3 adjudication task (order-swap done by caller)."""

from typing import Any

from backend.app.core.hashing import canonical_json
from backend.app.llm.tasks_other import AdjudicationVerdict
from backend.app.llm.tasks_other import L3_SYSTEM


def adjudication_user(
    name_a: str, source_a: str, name_b: str, source_b: str, country: str, det: dict[str, Any]
) -> str:
    return canonical_json(
        {
            "name_a": name_a,
            "source_a": source_a,
            "name_b": name_b,
            "source_b": source_b,
            "country": country,
            "deterministic": det,
        }
    )


async def adjudicate(llm: Any, model: str, user: str) -> AdjudicationVerdict:
    out = await llm.structured(
        task="adjudicate names",
        model=model,
        system=L3_SYSTEM,
        user=user,
        schema=AdjudicationVerdict,
        max_tokens=2048,
    )
    assert isinstance(out, AdjudicationVerdict)
    return out
