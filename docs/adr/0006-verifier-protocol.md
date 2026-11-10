# ADR 0006 — Verifiers behind Verifier Protocol, mocked at Phase 0
## Context
Real IRS/GST/VIES unavailable in demo (A-03; B §9.S4).
## Decision
Production-shaped Verifier protocol now; NoopVerifier + fixture schema in Phase 0; real mocks Phase 2.
## Consequences
Swap-in later without engine change; contract-tested.
## Alternatives Considered
SDK-specific wrappers — rejected: coupling.
