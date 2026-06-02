# Fix Cross-Context Dependency Violations

## Context

This is a multi-bounded-context event-sourced C# / .NET 8 monorepo. The modules live under `src/modules/`. The bounded contexts are: Catalog, AssetManagement, ChangeRequests, DocumentSigning, Metadata, Processing, Registration.

Each context follows this layer structure:
- `*.Domain` — aggregates, domain events, value objects (including strongly-typed IDs). No cross-context references allowed.
- `*.Contracts` — integration events only. All IDs must be raw primitives (`string`, `Guid`, `long`). No domain type references.
- `*.WriteModel` — command handlers. May reference own `*.Domain`, own `*.Contracts`, and other contexts' `*.Contracts` only.
- `*.WriteModel.Infrastructure` — same rules as WriteModel.
- `*.ReadModel` — projections / read models. May reference own `*.Domain` only.
- `*.ReadModel.Infrastructure` — same rules as ReadModel.

## Rules (non-negotiable)

1. **`*.Domain` projects must have zero `ProjectReference` entries pointing to any other context.** They are fully self-contained.
2. **`*.Contracts` projects must use only primitives** (`string`, `Guid`, `long`, `bool`, `DateTimeOffset`, etc.) for all IDs and references. No domain value-object types.
3. **`*.WriteModel` and `*.WriteModel.Infrastructure` must not reference another context's `*.Domain` or `*.WriteModel`.** Only `*.Contracts` cross-context references are allowed.
4. **`*.ReadModel` and `*.ReadModel.Infrastructure` must not reference another context's `*.Domain`.** Only `*.Contracts` cross-context references are allowed.

Strongly-typed ID value objects (e.g. `MediaItemId`, `AssetId`) belong in the owning context's `*.Domain`. When another context needs to carry one of these IDs as a correlation field, it uses `string` or `Guid` — not the foreign typed wrapper.

## What to do

### Step 1 — Audit all `.csproj` files

Scan every `.csproj` under `src/modules/` for `ProjectReference` entries that cross context boundaries in violation of the rules above. Concretely, flag:

- Any `*.Domain.csproj` that has a `ProjectReference` to another context's project
- Any `*.Contracts.csproj` that has a `ProjectReference` to any `*.Domain`
- Any `*.WriteModel.csproj` or `*.WriteModel.Infrastructure.csproj` that references another context's `*.Domain` or `*.WriteModel`
- Any `*.ReadModel.csproj` or `*.ReadModel.Infrastructure.csproj` that references another context's `*.Domain`

Known violations to start with (verify these and find any others):
- `Catalog/Catalog.ReadModel.Infrastructure` → `AssetManagement.Domain`
- `Catalog/Catalog.WriteModel.Infrastructure` → `Registrations.Domain`
- `ChangeRequests/ChangeRequests.WriteModel` → `Catalog.WriteModel`
- `ChangeRequests/ChangeRequests.WriteModel.Infrastructure` → `Catalog.WriteModel.Infrastructure`

### Step 2 — For each violation, determine the fix

For each bad `ProjectReference`:

a. Read the files in the referencing project that actually use types from the bad dependency.
b. Determine what they're using: typically a typed ID, a value object, or a command/handler type.
c. Apply the correct fix:
   - If a `*.ReadModel.Infrastructure` or `*.WriteModel.Infrastructure` uses a typed ID from another context's `*.Domain` — replace the typed ID with `string` (parse/format at the boundary) and replace the `ProjectReference` with the context's `*.Contracts` if needed, or remove it entirely.
   - If a `*.WriteModel` references another context's `*.WriteModel` to call a command handler — this is an architectural violation. The correct pattern is to publish an integration event (via `*.Contracts`) and let the receiving context's handler react. Flag this for manual review with a clear comment explaining what the code is currently doing across the boundary.
   - If a `*.Contracts` project uses a typed ID from `*.Domain` — replace the typed ID with `string`.

### Step 3 — Apply fixes

Make all mechanical fixes (typed ID → `string`, remove bad `ProjectReference`, add `*.Contracts` reference if not already present). Do not change any business logic.

For any `*.WriteModel` → `*.WriteModel` violation that requires architectural judgment, do not silently rewrite it. Instead, leave the code as-is, remove only if clearly safe, and add a `// TODO(architecture): ...` comment explaining the violation and what the correct pattern should be.

### Step 4 — Verify

Run `dotnet build src/Media.sln` (or the solution file at the root of `src/`). Fix any compilation errors that result from the changes. The build must pass cleanly before finishing.

### Step 5 — Report

Print a summary of:
- Every violation found (project → bad dependency)
- What was done to fix each one (or why it was flagged for manual review instead)
- Final build status
