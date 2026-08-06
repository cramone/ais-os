# ADR-005 — Single Dedicated Application Database

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The application requires persistent storage for:

1. Its own state — `CleanupRun` records, per-document and per-folder tracking, phase logs.
2. Hangfire's job persistence — queued jobs, states, continuations, retry records.

The MAGIQ Documents database is a separate third-party database accessed directly for Steps 1, 2, and 5. It is not the application's database.

Two options were considered:
- **Two dedicated databases** — one for app state, one for Hangfire.
- **One dedicated database** — app state and Hangfire tables co-located, separate from the MAGIQ Documents database.

---

## Decision

Use a **single dedicated SQL Server database** for both the application's own state tables and the Hangfire tables.

- The database is **separate from the MAGIQ Documents database** — no mixing of app tables with the client's records-management schema.
- Hangfire's schema lives alongside `CleanupRun` and related tables in this one database.
- Two connection strings in configuration: `AppDatabase` (this database) and `MagiqDocumentsDatabase` (MAGIQ, read-only access for SQL queries).

---

## Consequences

- Single database to provision, back up, and maintain — appropriate for a single-server, once-a-year tool.
- Hangfire's built-in schema migration runs against `AppDatabase` on startup.
- Splitting into two databases later is straightforward if operational requirements change.
- The `ProcessTicket` column on `CleanupRun` (see ADR-007) is in this database — recycle-safe by design.
