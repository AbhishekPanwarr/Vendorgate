# ADR 0005 — SQLite WAL now, Postgres-ready schema
## Context
Zero-ops live demo vs portability (B §6).
## Decision
SQLite WAL via connect-listener pragma; all column types Postgres-compatible.
## Consequences
One-file demo; migrate by changing URL.
## Alternatives Considered
Postgres from day 0 — rejected: ops burden for skeleton.
