# ADR 0002 — Fail-closed on UNVERIFIABLE
## Context
Verifier outages must not become passes (B §3, §9.S4).
## Decision
Mandatory UNVERIFIABLE blocks approval (PENDING INTERNAL).
## Consequences
Outage toggle demo goes Pending, never Approved.
## Alternatives Considered
Retry-then-pass — rejected: opens fraud hole.
