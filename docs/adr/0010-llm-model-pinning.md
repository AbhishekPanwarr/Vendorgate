# ADR 0010 — LLM model pinning (Meta Model API)

## Context

Phase 3 needs a live LLM for the one-time cache-record step; CI and demo run
in replay. Derives from D-3.2 env guards.

## Decision

- Provider: Meta Model API, OpenAI-compatible, `https://api.meta.ai/v1`.
- `LLM_MODEL_FAST=muse-spark-1.3`, `LLM_MODEL_STRONG=muse-spark-1.3`.
- Key from local `.env` (`MODEL_API_KEY`, never committed).
- Default `max_tokens=2048`: reasoning models consume the budget on reasoning
  first; small budgets return empty content with `finish_reason=length`.
- Record step kept small (PoC set only); replay fixtures committed.

## Consequences

Live calls are rare and deliberate; everything else replays.

## Alternatives Considered

Anthropic direct — rejected: no key available; Meta endpoint is compatible.
