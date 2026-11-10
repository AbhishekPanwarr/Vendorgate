# ADR 0004 — Custom async DAG orchestrator
## Context
Need per-check events + memoization + unit-testability (B §9).
## Decision
~300-line anyio task-group executor; openapi.json regen is a deliberate PR with diff review.
## Consequences
Full control of events/fingerprints; we own the code.
## Alternatives Considered
n8n/Temporal/LangGraph — rejected: hide control flow or overkill.
