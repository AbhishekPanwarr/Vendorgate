# ADR 0003 — Record/replay LLM cache with pinned models
## Context
Deterministic CI + offline demo (B §11).
## Decision
Cache keyed by sha256(model+prompt+schema+input); modes live/record/replay/off; replay in CI/demo.
## Consequences
Free, offline-capable, disclosed in video.
## Alternatives Considered
Live-only — rejected: flaky demo, costly CI.
