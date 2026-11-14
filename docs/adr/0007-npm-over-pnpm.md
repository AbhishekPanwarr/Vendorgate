# ADR 0007 — npm over pnpm
## Context
Spec said pnpm; env has node 25 + npm only. Derives from build practicality.
## Decision
Use npm (`npm ci`/`npm run build`) for Phase 0 skeleton.
## Consequences
Makefile/CI use npm; one-line deviation, no behavior change.
## Alternatives Considered
Install pnpm via corepack — rejected: extra failure mode for a skeleton UI.
