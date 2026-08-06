# ADR-010 — Application Database Access: Dapper + Thin Repositories, DbUp Migrations

**Date:** 2026-07-23
**Status:** Accepted

---

## Context

The application persists its own workflow state — `CleanupRun` and the related
`CleanupRunFolder`, `CleanupRunDocument`, `CleanupRunPhaseLog` tables (ADR-002) —
in the single dedicated application database (ADR-005). ADR-004 chose **Dapper**
for the read-only MAGIQ Documents SQL (Steps 1, 2, 5), but deliberately left the
access technology for the app's *own* tables open: Dapper vs EF Core vs a
micro-ORM. A schema creation and versioning mechanism is also required — a
baseline for the four tables now, and forward changes as later stories (34135,
34137, 34139+) add columns and tables.

This ADR resolves both, ahead of Story 34131 (the persistence spine).

---

## Decision

1. **Dapper over `Microsoft.Data.SqlClient`, wrapped in thin per-aggregate
   repositories** (e.g. an `IRunStore` in `Persistence/`). Hand-written SQL, no
   ORM model, no change tracking. This is the same data-access idiom as the
   MAGIQ SQL path (ADR-004) — one style across the codebase.

2. **Schema managed by DbUp** — embedded, ordered, forward-only SQL scripts
   applied at startup and journaled in a `SchemaVersions` table. The baseline
   script (`0001_baseline.sql`) creates the four `CleanupRun*` tables per
   `dev-spec.md`. Later stories add numbered scripts rather than editing the
   baseline.

3. **Hangfire owns its own schema.** `UseSqlServerStorage(prepareSchemaIfNecessary)`
   creates and migrates Hangfire's tables in the same `AppDatabase` (ADR-005).
   DbUp does **not** manage Hangfire tables — the two schema owners coexist in
   one database by convention.

4. **Connection via a scoped `IAppDbConnectionFactory`** returning a
   `SqlConnection` built from the `AppDatabase` connection string. No ambient
   static connections.

---

## Consequences

- One data-access idiom (Dapper) across the app DB and the MAGIQ DB — nothing
  new to learn versus ADR-004, and no `Magiq.Platform.*` / ORM coupling.
- SQL is explicit and reviewable, which suits a records-management audit context.
- More hand-written boilerplate than EF Core's change tracking — accepted for a
  bounded, well-known schema on a single-server annual tool.
- DbUp gives journaled, forward-only migrations. No down-migrations; a corrective
  is a new forward script. Acceptable for on-prem, operator-run deployment.
- Startup order matters: apply DbUp migrations, and let Hangfire prepare its own
  schema, before the Hangfire server begins processing.
- Adds three packages with Story 34131: `Dapper`, `Microsoft.Data.SqlClient`,
  `dbup-sqlserver` (Hangfire packages tracked separately). `Microsoft.Data.SqlClient`
  is shared with the later MAGIQ Dapper story (34133).

---

## Alternatives considered

- **EF Core** — richer tooling (LINQ, code-first migrations) but a heavy
  dependency and an ORM model over what is a workflow, not a rich aggregate;
  against the deliberate no-ORM, no-platform grain.
- **Micro-ORM helper (Dapper.Contrib / RepoDb)** — trims CRUD boilerplate over
  raw Dapper, but adds a package for marginal benefit on a small table set.
- **Hand-rolled idempotent schema runner** (no migration package) — zero new
  dependency, but no version journal and weaker rigor as the schema evolves
  across the remaining epic.
