"""Claude provider (Anthropic tool-use structured output)."""

import os

from pydantic import BaseModel


class ClaudeProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set (fail-closed on model pinning)")
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def structured(
        self,
        *,
        task: str,
        model: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        max_tokens: int = 1024,
    ) -> BaseModel:
        tool = {"name": "result", "description": task, "input_schema": schema.model_json_schema()}
        for attempt in range(2):
            msg = await self._client.messages.create(  # type: ignore[call-overload]
                model=model,
                system=system,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "result"},
                temperature=0,
            )
            blocks = [b for b in msg.content if getattr(b, "type", "") == "tool_use"]
            if not blocks:
                continue
            try:
                out = schema.model_validate(blocks[0].input)
                usage = getattr(msg, "usage", None)
                used = (getattr(usage, "input_tokens", 0) or 0) + (
                    getattr(usage, "output_tokens", 0) or 0
                )
                out._tokens_used = used  # type: ignore[attr-defined]
                return out
            except Exception:
                if attempt == 0:
                    user = user + "\n\nPrevious output failed schema validation; fix it."
                    continue
                raise
        raise ValueError("LLM returned no tool output")


def required_models() -> tuple[str, str]:
    fast = os.environ.get("LLM_MODEL_FAST", "")
    strong = os.environ.get("LLM_MODEL_STRONG", "")
    if not fast or not strong:
        raise ValueError("LLM_MODEL_FAST and LLM_MODEL_STRONG must be set")
    return fast, strong
