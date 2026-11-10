# ADR 0001 — Deterministic core with bounded LLM
## Context
PS-2 demands explainable approve/pending/reject; solution B §3/§11.
## Decision
Status computed by pure functions from findings; LLM only extracts/adjudicates/drafts, never lowers severity without deterministic corroborator.
## Consequences
Prompt injection cannot approve; adjudication path required.
## Alternatives Considered
End-to-end LLM — rejected: non-deterministic, unauditable.
