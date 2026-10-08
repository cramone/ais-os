---
id: MM-078
type: plan
project: magiq-media
workstream: WS-56-remove-host-rotation-seeding
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, projections, rotation, read-model-metadata]
consumes: []
blocked-by-external: []
status: new
branches: [feature/guid-projection-rotation]
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/projections/INDEX.md#WS-56 (no gap file; row-tracked); no separate review document.
---

# WS-56 — Hosts do not seed `read-model-metadata`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Branch:** `feature/guid-projection-rotation` (unmerged; 5 commits ahead of `main`). This lands **before** that branch's PR to `main`, so host seeding never reaches a release.
**Depends on:** none
**Pairs with:** MM-077 (WS-55) — the CDK seeds the rows

**Spec:**
- `system-architecture.md` § Seeding: "Hosts read `read-model-metadata` and never write it, at startup or otherwise."
- Where the CDK does not run, `ProjectionsTableMigration` seeds each row at the deployed version.

**On the branch today:**
- `7d4c36b8` registers `RotationMetadataSeederService`, an `IHostedService`, inside `UseDynamoDbStore`. Every projection-using host therefore seeds at startup.
- Cost: about 24 conditional `PutItem`s per cold start, nearly all refused.
- In QueryApi, which has `grantReadData` only, it logs `AccessDeniedException` at Error on every cold start.

**Keep the migration path.** `IRotationMetadataSeeder` / `RotationMetadataSeeder` stay, together with their `TryAddSingleton` registration. `ProjectionsTableMigration.CreateAsync` keeps calling `SeedAsync`, so development environments without the CDK still get their rows.

## Session invocation

Open a new Claude Code session and `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Check out `feature/guid-projection-rotation`. Paste:

> Picking up WS-56 (plan MM-078). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-56-remove-host-rotation-seeding\WS-56-remove-host-rotation-seeding-plan.md`.
>
> Remove host-startup seeding of `read-model-metadata`: drop the `AddHostedService<RotationMetadataSeederService>()` registration and the service class; keep `IRotationMetadataSeeder` / `RotationMetadataSeeder` for `ProjectionsTableMigration`. Rewrite every comment that says seeding runs at startup or in every host. Also correct the `GuidFactory` remark dated "Fixed 2026-08-24". Read `CLAUDE.md` first.

## Phase 0 — Scope confirmation
- [x] ~~Locate host seeding~~ — `ProjectionsBuilderExtensions.cs:186-199`, `Replay/Metadata/RotationMetadataSeederService.cs`
- [x] ~~Confirm `Microsoft.Extensions.Hosting` is used only by the service~~ — only `RotationMetadataSeederService.cs` in `Magiq.Platform.Projections.Stores.DynamoDb`
- [ ] Confirm no other assembly references `RotationMetadataSeederService`

## Phase 1 — Remove host seeding
- [ ] `ProjectionsBuilderExtensions`: delete `services.AddHostedService<RotationMetadataSeederService>()` and its comment block
- [ ] Delete `Replay/Metadata/RotationMetadataSeederService.cs`
- [ ] Remove `<PackageReference Include="Microsoft.Extensions.Hosting.Abstractions"/>` from `Magiq.Platform.Projections.Stores.DynamoDb.csproj` (now unused)
- [ ] Keep `services.TryAddSingleton<IRotationMetadataSeeder, RotationMetadataSeeder>()`; its comment says it serves `ProjectionsTableMigration`

## Phase 2 — Comments state the specified model
Every comment below currently says seeding runs at startup, in every host, or "unconditionally". It should say instead: in deployed environments the IaC deploy seeds the rows; `ProjectionsTableMigration` seeds them where migrations run; hosts only read.
- [ ] `ProjectionsBuilderExtensions.cs:186-197`
- [ ] `ProjectionsTableMigration.cs` class remarks (`:20-30`) and the `CreateAsync` comment (`:53-59`)
- [ ] `IRotationMetadataSeeder.cs` remarks ("safe to call on every startup")
- [ ] `RotationMetadataSeeder.cs` remarks — keep the explanation of why the pin matters and the `attribute_not_exists` guarantee; drop "every startup"
- [ ] `ProjectionRotationOrchestrator.cs:132` — "The startup seeder normally creates this row" → "The deploy normally seeds this row"
- [ ] `GuidFactory.cs` remark "Fixed 2026-08-24" — not true until this branch merges; reword to state the property without a date, or date it at merge

## Phase 3 — Tests
- [ ] `ProjectionRotationIntegrationFixture` still builds `ProjectionsTableMigration` with `IRotationMetadataSeeder` and passes
- [ ] Add: a host built with `UseDynamoDbStore` registers no `IHostedService` from this package
- [ ] `dotnet build` + `dotnet test` green

## Phase 4 — Ship
- [ ] Commit on `feature/guid-projection-rotation`
- [ ] Included in that branch's PR to `aspnetcore-platform/main`. No package bump here — Chase's policy is to bump once all dependency-gap plans are implemented.

## Phase 5 — Close
- [ ] `docs/dependency-gaps/projections/INDEX.md`: WS-56 → § Shipped
- [ ] `docs/dependency-gaps/INTEGRATION-BACKLOG.md`: MM-078 → § Shipped

## Closing out

The plan's card moves to `done` only after Chase agrees the work is implemented and complete. The closing card comment records every branch the work was committed to.

## Session log
- 2026-10-08: plan drafted from the review of `feature/guid-projection-rotation`. Chase ruled hosts must not seed (startup delay); the CDK seeds instead (MM-077), and the migration seeding stays for development environments. Folded in the `GuidFactory` comment correction for the same PR.
