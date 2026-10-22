# JWT challenge diagnostics + claim-name alignment — plan

**Status:** Future work · drafted 2026-10-21 · not yet in review cycle
**Project:** mgq-dotnet-platform
**Workstream:** `jwt-challenge-diagnostics`
**Prefix:** AP-TBD (mint next free id when a review is raised — strict review-first convention; see `../../CLAUDE.md § Review → Plan cycle`)
**Consumed by:** magiq-media PR #196 operator experience; every future magiq-* service that calls `AddMagiqCloudJwt`

> **Review-first exception.** This plan is drafted ahead of its review so the requirements aren't lost between QA stabilization and the next SDK-planning window. When this work picks up, raise `reviews/jwt-challenge-diagnostics/jwt-challenge-diagnostics-review-<date>.md` first per adoption marker in `../../CLAUDE.md`, then rename this plan to match the review filename.

---

## Problem

Two gaps surfaced in `TenantResolutionBuilder` during magiq-media release stabilization (release/1.0.0 QA token work):

### Gap 1 — Silent 401 on tenant-binding failure

`AddMagiqCloudJwt` wires an `OnTokenValidated` handler at `src/aspnetcore/MultiTenancy/Magiq.AspNetCore.Tenants.Resolution/TenantResolutionBuilder.cs:311-379` that calls `ctx.Fail(string message)` when the token lacks the configured tenant claim or the value doesn't match the resolved identifier. The resulting `AuthenticationFailureException` is a plain exception; it doesn't match any `SecurityToken*` branch in `JwtBearerHandler.HandleAuthenticateAsync`, so:

- `WWW-Authenticate` on the 401 carries only `error="invalid_token"` — no `error_description`.
- `OnAuthenticationFailed` doesn't fire (that event is only raised from the catch block for `SecurityTokenException` subtypes).
- Caller sees a bare 401 with zero diagnostic signal; operator has no log line to grep.

Observed in magiq-media PR #196 — the HS256 token path validated signature, failed tenant-binding on `MagiqCloud__TenantClaimName=client_id` (token carried `tenant_id`), and the only path to a diagnosis was a `OnTokenValidated` chain handler written in the app's `Program.cs`. That logger worked, confirmed the branch, and informed the fix (flip to `tenant_id`). The experience should be: platform does the logging + optional response-side surfacing automatically, no per-service wiring.

### Gap 2 — Hardcoded `client_id` in claims mapper

`TenantResolutionBuilder.cs:274`:

```csharp
identity.AddOrReplace(securityOptions.TenantIdClaim, identity.FindFirst("client_id")?.Value);
```

Hardcoded to `client_id`, independent of the configured `MagiqCloudTenantClaimName`. For tokens that carry only `tenant_id` (magiq-auth HS256 flow today), the mapper writes null and falls through to the `TenantSettings` fallback at lines 275-279. Works via tenant store resolution, but the mapper is inconsistent with the enforcement check at line 337 which does read the configured claim name. Two sources of truth = subtle divergence waiting to surface.

---

## Scope

| # | Change | Severity |
|---|---|---|
| 1 | Add `OnChallenge` + chained `OnTokenValidated` logger via `IPostConfigureOptions<JwtBearerOptions>` inside `AddMagiqCloudJwt`; optional response-side detail surfacing via `Authentication:ExposeChallengeDetails` config flag (default `false`) | Primary — unblocks operator diagnosability for every consumer |
| 2 | Change `TenantResolutionBuilder.cs:274` claims mapper to read the configured `capturedClaimName` instead of hardcoded `"client_id"` | Secondary — correctness alignment |
| 3 | Docs + ADR entry + CHANGELOG | Required alongside shipping |

---

## Change 1 — Challenge diagnostics (PRIMARY)

### Location

`src/aspnetcore/MultiTenancy/Magiq.AspNetCore.Tenants.Resolution/TenantResolutionBuilder.cs`, inside `AddMagiqCloudJwt` after the existing `tenantServices.Configure<JwtBearerOptions>(...)` call (currently line 293-302).

### Code shape

```csharp
tenantServices.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
    .PostConfigure<IConfiguration, ILoggerFactory>((options, config, loggerFactory) =>
    {
        var exposeDetails = config.GetValue("Authentication:ExposeChallengeDetails", defaultValue: false);
        var logger = loggerFactory.CreateLogger("Magiq.AspNetCore.Tenants.Resolution.JwtDiagnostics");

        options.Events ??= new JwtBearerEvents();

        var challengePrior = options.Events.OnChallenge;
        options.Events.OnChallenge = async ctx =>
        {
            if (challengePrior is not null) await challengePrior(ctx);

            var failure = ctx.AuthenticateFailure;
            if (failure is null) return;

            logger.LogWarning(failure, "JWT challenge: {Message}", failure.Message);

            if (exposeDetails && string.IsNullOrEmpty(ctx.ErrorDescription))
            {
                ctx.ErrorDescription = failure.Message;
            }
        };

        var validatedPrior = options.Events.OnTokenValidated;
        options.Events.OnTokenValidated = async ctx =>
        {
            if (validatedPrior is not null) await validatedPrior(ctx);

            if (ctx.Result is { Succeeded: false, Failure: { } fail })
            {
                logger.LogWarning(fail, "JWT post-validation Fail: {Message}", fail.Message);
            }
        };
    });
```

### Config contract

- **`Authentication:ExposeChallengeDetails`** — `bool`, default `false`. When `true`, `error_description` on `WWW-Authenticate` carries the failure message. When `false` (prod default), only the server log carries the detail; wire response stays opaque to avoid leaking tenant/claim hints to anonymous callers.
- Logging fires regardless of this flag. Operators always get the signal; only external disclosure is gated.
- Hosts opt in per environment:
  ```
  Authentication__ExposeChallengeDetails=true    # dev / qa
  Authentication__ExposeChallengeDetails=false   # staging / prod
  ```

### Chaining semantics

- MUST capture prior `OnChallenge` and `OnTokenValidated` and `await` them first so any existing or future handlers (e.g. from `AddPerTenantJwtBearer` or consumer-side `PostConfigure`) still run. The platform's existing `OnTokenValidated` chain at line 311-379 (`enforceTenantBinding` path) is one such caller.
- MUST gate the `OnChallenge` body on `ctx.AuthenticateFailure` being non-null. Challenges fire with no failure context when there's no bearer header; those should not log noise.
- MUST gate the `OnTokenValidated` log on `Succeeded == false`. Successful validations also fire the event; don't want a per-request log line.

### Non-functional

- Zero behavior change when no failures occur.
- Zero behavior change for consumers with no `Authentication:ExposeChallengeDetails` config set.
- Backwards compatible with every existing consumer — no new method signature on `AddMagiqCloudJwt`.

---

## Change 2 — Claim-name alignment in mapper (SECONDARY)

### Location

`src/aspnetcore/MultiTenancy/Magiq.AspNetCore.Tenants.Resolution/TenantResolutionBuilder.cs:274`, inside the `AddJwtClaimsMapper` body registered under `AddMagiqCloudJwt`.

### Change

**Current (hardcoded):**
```csharp
identity.AddOrReplace(securityOptions.TenantIdClaim, identity.FindFirst("client_id")?.Value);
```

**Target:**
```csharp
identity.AddOrReplace(securityOptions.TenantIdClaim, identity.FindFirst(capturedClaimName)?.Value);
```

`capturedClaimName` is already in scope at line 288 — the configured `MagiqCloudTenantClaimName`.

### Rationale

Mapper now consistent with the enforcement check at line 337. Both read the same configured claim. HS256 tokens carrying only `tenant_id` get their value mapped to `TenantIdClaim` directly instead of falling through to `TenantSettings` resolution.

### Backwards-compat

- Consumers with `MagiqCloudTenantClaimName=client_id` + tokens carrying `client_id`: identical behavior.
- Consumers with `MagiqCloudTenantClaimName=tenant_id` + tokens carrying `tenant_id`: now consistent — mapper + enforcement read the same claim.
- Consumers with tokens missing the configured claim: still fall through to `TenantSettings` fallback. Unchanged.

---

## Change 3 — Docs + ADR + CHANGELOG

### README

Update `src/aspnetcore/MultiTenancy/Magiq.AspNetCore.Tenants.Resolution/README.md` with new section under `## Per-tenant JWT Bearer`:

```markdown
### Challenge diagnostics

`AddMagiqCloudJwt` wires `OnChallenge` and `OnTokenValidated` chain handlers
that log any `AuthenticateFailure.Message` from token-validation or
tenant-binding failures. Both messages route through
`ILogger<"Magiq.AspNetCore.Tenants.Resolution.JwtDiagnostics">` at `Warning`.

Response-side detail surfacing is opt-in via config:

| Key | Default | Effect |
|---|---|---|
| `Authentication:ExposeChallengeDetails` | `false` | When `true`, `WWW-Authenticate` on 401 responses carries `error_description=<message>`. When `false`, server log carries the detail but the wire stays opaque. |

Enable in dev/qa for debugging; leave `false` in prod to avoid leaking
tenant/claim hints to anonymous callers. Logging fires regardless.
```

### ADR

New file `adrs/jwt-challenge-diagnostics.md`:

> **Context:** `ctx.Fail(string)` in platform tenant-binding → silent 401, no log, no description. Noticed during magiq-media release stabilization.
> **Decision:** platform wires `OnChallenge` + chained `OnTokenValidated` logger via `IPostConfigureOptions<JwtBearerOptions>` inside `AddMagiqCloudJwt`. Response surfacing opt-in via `Authentication:ExposeChallengeDetails`.
> **Consequences:** every consuming service gets diagnostics for free. Prod ops decide whether to leak hints via config.
> **Alternatives rejected:** per-service wiring (duplicates boilerplate across every magiq-* host); switching platform's `ctx.Fail` to throw `SecurityTokenException` (changes handler semantics + risks downstream subclass logic).

### CHANGELOG

```
### Added
- Challenge + token-validated diagnostics on the magiqcloud JWT bearer scheme —
  tenant-binding failures (missing/mismatched tenant claim) now emit server logs
  and, optionally, populate `error_description` on 401 responses. Opt-in via
  `Authentication:ExposeChallengeDetails`.

### Changed
- `AddMagiqCloudJwt` claims mapper now reads the configured tenant claim name
  consistently (previously hardcoded to `client_id`). Consumers whose tokens
  carry both `client_id` and the configured claim see unchanged behavior.
```

---

## Tests

Add unit tests to `src/aspnetcore/MultiTenancy/Magiq.AspNetCore.Tenants.Resolution.Tests` (create if absent):

| Test | Expectation |
|---|---|
| `OnTokenValidated_WhenClaimMissing_LogsFailureMessage` | `ILogger<JwtDiagnostics>` received a warning with the Fail message |
| `OnChallenge_WhenAuthenticateFailureSet_SurfacesDescription_WhenExposeDetailsTrue` | `WWW-Authenticate` carries `error_description` |
| `OnChallenge_WhenAuthenticateFailureSet_OmitsDescription_WhenExposeDetailsFalse` | wire response bare, log line still written |
| `OnChallenge_PriorHandlerStillFires` | pre-existing handler chained correctly |
| `OnTokenValidated_SuccessfulValidation_LogsNothing` | regression guard — no log on success |
| `JwtClaimsMapper_ReadsConfiguredClaimName` | mapper reads `tenant_id` when config says so |
| `JwtClaimsMapper_FallsThroughToTenantSettings_WhenConfiguredClaimMissing` | fallback preserved |
| `JwtClaimsMapper_StillWorks_WhenConfiguredClaimIsDefaultClientId` | default behavior preserved |

---

## Acceptance criteria

1. New `PostConfigure` registered on `JwtBearerDefaults.AuthenticationScheme` emits a `Warning` log line for both `OnChallenge` (with `AuthenticateFailure`) and `OnTokenValidated` (with `Result.Failure`).
2. `Authentication:ExposeChallengeDetails=true` → `WWW-Authenticate` carries `error_description=<message>` on 401.
3. `Authentication:ExposeChallengeDetails=false` or unset → log fires, response unchanged from today.
4. Pre-existing `OnTokenValidated` enforcement handler (platform's tenant-binding check) still runs — chaining preserves order.
5. Claims mapper at line 274 reads `capturedClaimName`, not literal `"client_id"`.
6. All 8 unit tests above green.
7. README + ADR + CHANGELOG entries land in same commit.

---

## Release gate

**Delivery is not "merged to develop" for this SDK.**

Per `../../CLAUDE.md § Review → Plan cycle`:
> This SDK is consumed as NuGet, not by project reference — `Directory.Packages.props` in each consumer pins `$(MagiqPlatformVersion)`. A contract change here is therefore not done when it merges: it is done when the packages are published and the consumer's version is bumped. Plans in this project state the release step explicitly rather than assuming it.

Release steps after merge:
1. Bump `Magiq.AspNetCore.Tenants.Resolution` package version per SemVer. This change is additive + behaviorally backwards-compatible → **minor** version bump.
2. Publish package to the `MAGIQSoftware` Azure DevOps feed.
3. Bump `$(MagiqPlatformVersion)` in `magiq-media` `Directory.Packages.props` (follow-up PR there).
4. Smoke a `/v1/auth/whoami` 401 against magiq-media QA — confirm the new log line lands in CloudWatch (`JwtDiagnostics` logger) and, with `ExposeChallengeDetails=true` on dev/qa, `error_description` populates.
5. Delete the app-side `OnAuthenticationFailed` logger wired in magiq-media's `Startup.cs` for the JWT fix (if any was left behind — current hotfix shape has none, but the diagnostic version shipped during stabilization did).

Only when a consumer bumps + validates can this be considered done.

---

## Downstream cleanup

Once this ships + magiq-media bumps the package:

- **magiq-media `Startup.cs`** — no app-side JWT logger today in the hotfix shape (PR #196 shipped lean). Nothing to delete there.
- **magiq-media `Program.cs`** — no diagnostic PostConfigure in the merged shape. Nothing to delete there.
- Every magiq-* service picks up the diagnostics on SDK bump. No app-side wiring required.

---

## Dependencies

- **None.** Pure SDK change; no cross-repo coordination required to merge the platform PR itself.
- Release step (NuGet publish + consumer bump) is downstream of merge.

---

## Related

- magiq-media PR #196 — `fix(auth): accept HS256 tokens alongside OIDC via Authentication:SigningKey`. Operator surface that would have been easier to debug with platform-side diagnostics.
- magiq-media infra PR #102 — `fix(deploy): hardcode MagiqCloud__TenantClaimName=tenant_id`. Same incident window; moved the config value that triggered the silent 401 before the diagnostic path existed.

---

## Non-goals

- No change to the `AddPerTenantJwtBearer` symmetric-key path. Separate concern.
- No change to the shape of `WWW-Authenticate` beyond `error_description` population. Error code strings and the challenge format stay as-is.
- No new `Authentication:*` config keys beyond `ExposeChallengeDetails`.
- No breaking change on `SecurityOptions` / `AddMagiqCloudJwt` method signatures.

---

## Open questions

- **Q1:** Should `ExposeChallengeDetails` default differ by `IWebHostEnvironment` (dev=true, prod=false) rather than being a flat default? Current proposal: flat default `false`, hosts opt in explicitly. Rationale: fewer footguns in prod; dev opts in once in appsettings.
- **Q2:** Does `ILoggerFactory` reach the `PostConfigure<T1, T2>` resolver scope correctly in multi-tenant tenant-services container? Platform's own `AddPerTenantJwtBearer` only uses `PostConfigure<ITenantConfiguration>` (single generic). May need to resolve via tenant container's `IServiceProvider` instead. Verify during implementation.
- **Q3:** Should the ADR cover the `JwtClaimsMapper` claim-name alignment as a separate decision, or roll it into the diagnostics ADR as "while we were in there"? Current proposal: single ADR covering both — they share origin + release window.
