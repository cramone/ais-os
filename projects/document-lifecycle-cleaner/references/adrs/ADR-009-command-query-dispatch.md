# ADR-009 — Command/Query Dispatch via FastEndpoints Built-in Bus

**Date:** 2026-07-22  
**Status:** Accepted

---

## Context

The application follows a CQRS-lite vertical-slice methodology (decisions/log.md 2026-07-13): each FastEndpoints endpoint is a self-contained slice that dispatches to a command or query handler. A dispatch mechanism must be chosen.

The reference codebase `magiq-media` dispatches through its proprietary `Magiq.Platform.*` SDK (`ICommandDispatcher.SendAsync` / `IQueryDispatcher.QueryAsync`, returning a `Result<T, IError>`). That SDK is part of the AWS / DynamoDB / event-sourced platform and is **deliberately excluded** from this on-prem project (see `Directory.Packages.props` — the catalogue intentionally omits `Magiq.Platform.*`). An in-process, vanilla mechanism is required that reproduces the same ergonomics (dispatch → `Result` → map to HTTP) without that dependency.

At the time of this decision no command exists in the repo — only the handler-less `PingEndpoint`. So the pattern is being set before the first real slice is written.

Options evaluated:

| Option | Notes |
|---|---|
| **FastEndpoints built-in command bus** | `ICommand<TResult>` + `ICommandHandler<TCommand,TResult>`, dispatched via `command.ExecuteAsync(ct)`. In-process, request-scoped, no extra package. Mirrors the magiq-media dispatch shape. |
| MediatR | `ISender` + `IRequestHandler<TReq,TRes>`. Closest 1:1 to magiq-media; free pipeline behaviours (logging/validation). Adds a dependency the repo has so far avoided. |
| Plain handler interfaces | Inject handlers directly into endpoints, no bus. Simplest, zero deps, but no uniform dispatch and no cross-cutting behaviours. |

---

## Decision

Use **FastEndpoints' built-in in-process command bus** for command/query dispatch.

1. **Commands and queries are `sealed record`s** living in their feature folder, implementing `ICommand<Result<T>>`. Queries use the same primitive (a read-only command) rather than introducing a second abstraction.
2. **Handlers** implement `ICommandHandler<TCommand, Result<T>>`, live in the same feature folder, and stay thin — orchestration only, returning a `Result<T>`.
3. **Endpoints dispatch** via `await new XxxCommand(...).ExecuteAsync(ct)` and map the returned `Result<T>` to HTTP through a shared `DlcEndpoint<TReq,TRes>` base class (the DLC counterpart of magiq-media's `CatalogEndpoint.SendDomainErrorAsync`), using the error contracts in `spec/dev-spec.md`.
4. **Results, not exceptions**, for all domain outcomes.
5. **No new package** is added for dispatch — the mechanism ships with FastEndpoints, already in the catalogue.

---

## Consequences

- Reproduces the magiq-media ergonomics the team already knows, with zero additional dependency and no AWS-platform coupling.
- The FastEndpoints **command bus** (synchronous, request-scoped, in-process) is distinct from, and complementary to, the **Hangfire job queue** (ADR-001) used for long-running background pipeline phases. Commands orchestrate a single request; Hangfire jobs run the multi-phase pipeline. Do not conflate them.
- No built-in pipeline behaviours (logging, validation, transactions). If cross-cutting concerns are later needed, add them explicitly via FastEndpoints pre/post processors or handler decorators — revisit MediatR only if that ceremony grows.
- Validation stays where magiq-media puts it: strongly-typed value objects and guard clauses in handlers, surfaced as `Result` errors — not FluentValidation/FastEndpoints validators.
- A shared `Result<T>` type and the `DlcEndpoint` base class are prerequisites and are introduced with the first command-bearing slice.

---

## Sources

- Reference patterns extracted from `magiq-media` (Catalog module: `CreateFolderEndpoint`, `CatalogEndpoint`, command/handler pairs) — adapted from its `Magiq.Platform` dispatcher to the vanilla FastEndpoints bus.
- [Command Bus — FastEndpoints](https://fast-endpoints.com/docs/command-bus)
