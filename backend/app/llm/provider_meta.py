"""Meta Model API provider (Muse Spark, OpenAI-compatible).

Base: https://api.meta.ai/v1, key from MODEL_API_KEY.
Structured output via Chat Completions JSON mode, validated into schema.
"""

import os

from pydantic import BaseModel


class MetaProvider:
    def __init__(
        self, api_key: str | None = None, base_url: str = "https://api.meta.ai/v1"
    ) -> None:
        self.api_key = api_key or os.environ.get("MODEL_API_KEY", "")
        if not self.api_key:
            raise ValueError("MODEL_API_KEY is not set")
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key=self.api_key)
        self.base_url = base_url

    async def structured(
        self,
        *,
        task: str,
        model: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        max_tokens: int = 2048,
    ) -> BaseModel:
        # NOTE: reasoning models spend tokens on reasoning first; small budgets
        # return empty content with finish_reason=length. Keep >= 2048.
        import anyio

        schema_json = json_dumps(schema.model_json_schema())
        sys = (
            system + "\n\nRespond with a single JSON object matching this "
            f"JSON Schema:\n{schema_json}\nOutput ONLY the JSON object, no other text."
        )
        for attempt in range(2):
            resp = await anyio.to_thread.run_sync(
                lambda: self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": sys},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=0,
                )
            )
            text = _extract_json(resp.choices[0].message.content or "")
            try:
                out = schema.model_validate_json(text)
                usage = getattr(resp, "usage", None)
                used = (getattr(usage, "prompt_tokens", 0) or 0) + (
                    getattr(usage, "completion_tokens", 0) or 0
                )
                out._tokens_used = used  # type: ignore[attr-defined]
                return out
            except Exception:
                if attempt == 0:
                    user = user + "\n\nPrevious output failed schema validation; fix it."
                    continue
                raise
        raise ValueError("LLM returned no usable output")


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return "{}"
    return text[start : end + 1]


def json_dumps(obj: object) -> str:
    import json

    return json.dumps(obj)


def required_models() -> tuple[str, str]:
    fast = os.environ.get("LLM_MODEL_FAST", "muse-spark-1.3")
    strong = os.environ.get("LLM_MODEL_STRONG", "muse-spark-1.3")
    return fast, strong
