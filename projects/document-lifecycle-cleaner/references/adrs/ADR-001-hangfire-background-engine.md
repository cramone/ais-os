# ADR-001 — Hangfire as Background Pipeline Engine

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The process is a long-running, multi-phase pipeline (identification → review → archival → cleanup). The spec requires:

- Step 9 (document move) must **resume from the point of failure** with no rollback — a mid-run restart must not re-process already-moved documents.
- Step 11 (purge) runs as a **background system process** with no direct operator action.
- Phases must execute in strict order — Step 10 cannot start until Step 9 confirms complete.
- A once-a-year, operator-triggered, single-server deployment.

On-premises hosting removes the team's usual SQS/Lambda options. A persistent in-process job engine is required.

Candidates evaluated:

| Option | Notes |
|---|---|
| Hangfire | Persistent job storage, automatic retries, phase chaining via continuations, built-in dashboard, in-process hosting |
| `IHostedService` / `BackgroundService` | No persistence, no retries, no dashboard — fails resumability requirement |
| FastEndpoints built-in job queue | Not designed for long-running pipeline orchestration |
| Quartz.NET | Strong at cron/scheduling; persistence and clustering complexity irrelevant for single-server annual run |

---

## Decision

Use **Hangfire** for all background pipeline phases (archival, move, delete, purge).

- Chain phases with **Hangfire continuations** — each phase only starts once its predecessor confirms complete.
- Rely on Hangfire's persistence + automatic retries for Step 9 resumability.
- Run the Hangfire server **in-process** within the API. No separate job server; single-server deployment.
- Use the **Hangfire dashboard** for operator observability of job state.

---

## Consequences

- Resumability and background-purge requirements satisfied without custom state-machine retry logic.
- Hangfire introduces a dependency on its SQL Server storage schema — these tables live in the dedicated app database (see ADR-005).
- Dashboard access should be restricted to authenticated admin users (not open to all).
- `WorkerCount = 1` is appropriate — no concurrency or parallelism needed for an annual single-run process.
