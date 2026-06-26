# External Provider Config — DB Migration Plan

## Problem

`ExternalProviderConfig` objects live in `appsettings.json` under `MagiqAuth.ExternalProviders`. This is wrong because:

- Requires redeploy/restart to add, remove, or modify a provider
- Config is deployment-scoped, not tenant-scoped — all customers share the same providers
- Secrets (`ClientId`) sit in plaintext config files alongside other app settings
- No audit trail or admin UI for managing providers
- OIDC schemes are registered once at startup from static config; no way to react to tenant-level changes

## Target State

Provider configs stored in DB, loaded at startup and manageable at runtime via admin API. Registration in the OIDC middleware uses ASP.NET Core's dynamic scheme infrastructure so new providers can be added without restart.

---

## Architecture Decisions

### Storage: new `ExternalProvider` table (not Setting table)

The existing `Setting` table with `CustomerId` partitioning is already used for `CustomerSettings`. Shoehorning structured OIDC config into key/value rows (e.g. `externalprovider.magiqad.clientid`) is awkward and loses type safety.

A dedicated `ExternalProvider` entity is cleaner: one row per provider, FK to `Customer` for tenant-scoped providers, nullable FK for global providers.

### Dynamic scheme registration

ASP.NET Core supports runtime scheme addition via:
- `IAuthenticationSchemeProvider.AddScheme(AuthenticationScheme)`
- `IOptionsMonitorCache<OpenIdConnectOptions>` to inject per-scheme options

Schemes registered at startup from DB seed. Admin endpoints add/update/remove schemes at runtime through the same interfaces — no restart required.

### Client secret storage

`ClientSecret` should be encrypted at rest using the existing `IEncryptionService` (same pattern as `SecuritySettings.EncryptionKey`). Store ciphertext in DB; decrypt on load.

---

## Domain Model

### New entity: `ExternalProvider`

**File:** `src/MagiqAuth.Core/Domain/Configuration/ExternalProvider.cs`

```csharp
public class ExternalProvider : BaseEntity
{
    public string SchemaName { get; set; }        // OIDC scheme name, unique
    public string DisplayName { get; set; }
    public string Authority { get; set; }
    public string ClientId { get; set; }
    public string ClientSecretEncrypted { get; set; }  // nullable; encrypted
    public string CallbackPath { get; set; }
    public string SignedOutCallbackPath { get; set; }
    public string RemoteSignOutPath { get; set; }
    public string EmailClaimName { get; set; } = "Email";
    public bool GetClaimsFromUserInfoEndpoint { get; set; }
    public string ScopesJson { get; set; }        // JSON array, e.g. ["openid","email"]
    public bool IsGlobal { get; set; }            // true = available to all tenants
    public int? CustomerId { get; set; }          // null when IsGlobal = true
    public bool IsEnabled { get; set; } = true;
    public DateTime CreatedOnUtc { get; set; }
    public DateTime UpdatedOnUtc { get; set; }
}
```

`SchemaName` must be unique. Add unique index.

---

## Data Layer

### EF mapping

**File:** `src/MagiqAuth.Data/Mapping/Configuration/ExternalProviderMap.cs`

Standard `EntityTypeConfiguration<ExternalProvider>` with:
- `HasIndex(x => x.SchemaName).IsUnique()`
- `HasIndex(x => x.CustomerId)`
- Column lengths for string fields

### Migration script

**File:** `scripts/2.1.0/add_external_providers_table.sql`

```sql
CREATE TABLE ExternalProvider (
    Id            INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    SchemaName    VARCHAR(100) NOT NULL,
    DisplayName   VARCHAR(200) NOT NULL,
    Authority     VARCHAR(500) NOT NULL,
    ClientId      VARCHAR(300) NOT NULL,
    ClientSecretEncrypted VARCHAR(1000) NULL,
    CallbackPath  VARCHAR(200) NOT NULL,
    SignedOutCallbackPath VARCHAR(200) NULL,
    RemoteSignOutPath     VARCHAR(200) NULL,
    EmailClaimName        VARCHAR(100) NOT NULL DEFAULT 'Email',
    GetClaimsFromUserInfoEndpoint BIT NOT NULL DEFAULT 0,
    ScopesJson    VARCHAR(500) NULL,
    IsGlobal      BIT NOT NULL DEFAULT 1,
    CustomerId    INT NULL,
    IsEnabled     BIT NOT NULL DEFAULT 1,
    CreatedOnUtc  DATETIME NOT NULL,
    UpdatedOnUtc  DATETIME NOT NULL,
    UNIQUE INDEX IX_ExternalProvider_SchemaName (SchemaName),
    INDEX IX_ExternalProvider_CustomerId (CustomerId)
);
```

Seed data migration: a companion script (or startup task) reads existing providers from `appsettings.json` and inserts them into the table on first run.

---

## Service Layer

### Interface

**File:** `src/MagiqAuth.Services/Configuration/IExternalProviderService.cs`

```csharp
public interface IExternalProviderService
{
    Task<IList<ExternalProvider>> GetAllProvidersAsync(bool includeDisabled = false);
    Task<IList<ExternalProvider>> GetProvidersForCustomerAsync(int customerId);
    Task<ExternalProvider> GetBySchemaNameAsync(string schemaName);
    Task<ExternalProvider> GetByIdAsync(int id);
    Task InsertProviderAsync(ExternalProvider provider);
    Task UpdateProviderAsync(ExternalProvider provider);
    Task DeleteProviderAsync(int id);
}
```

### Implementation

**File:** `src/MagiqAuth.Services/Configuration/ExternalProviderService.cs`

- Standard repository pattern (same as `SettingService`)
- `GetProvidersForCustomerAsync` returns global providers + providers matching `customerId`
- Encrypt/decrypt `ClientSecret` via injected `IEncryptionService` 
- Cache results with short TTL (e.g. 5 min) using existing cache infrastructure

---

## Dynamic Scheme Registration

### Startup registration (replaces static loop in `ServiceCollectionExtensions`)

**File:** `src/MagiqAuth.Web.Framework/Infrastructure/DynamicOidcRegistration.cs`

New static helper called from `AddMagiqAuthentication`:

```csharp
public static class DynamicOidcRegistration
{
    public static void RegisterProviders(
        IAuthenticationBuilder authBuilder,
        IEnumerable<ExternalProvider> providers)
    {
        foreach (var p in providers.Where(x => x.IsEnabled))
        {
            authBuilder.AddOpenIdConnect(p.SchemaName, p.DisplayName, options =>
                ApplyOptions(options, p));
        }
    }

    public static void ApplyOptions(OpenIdConnectOptions options, ExternalProvider p)
    {
        // ... same options block currently in ServiceCollectionExtensions
    }
}
```

`AddMagiqAuthentication` resolves `IExternalProviderService` (via `BuildServiceProvider()` — same pattern as existing code) and calls `RegisterProviders`.

### Runtime add/update/remove

New service: `IDynamicAuthSchemeService`

```csharp
public interface IDynamicAuthSchemeService
{
    Task AddOrUpdateSchemeAsync(ExternalProvider provider);
    Task RemoveSchemeAsync(string schemaName);
}
```

Implementation injects:
- `IAuthenticationSchemeProvider`
- `IOptionsMonitorCache<OpenIdConnectOptions>`

`AddOrUpdateSchemeAsync`:
1. Call `_optionsCache.TryRemove(schemaName)` (noop if not present)
2. Call `_optionsCache.GetOrAdd(schemaName, () => BuildOptions(provider))`
3. If scheme doesn't exist: `_schemeProvider.AddScheme(new AuthenticationScheme(...))`

`RemoveSchemeAsync`:
1. `_optionsCache.TryRemove(schemaName)`
2. `_schemeProvider.RemoveScheme(schemaName)` (ASP.NET Core 8 exposes this)

---

## Admin API

New controller or extend existing admin endpoints.

**File:** `src/MagiqAuth.Api/Controllers/ExternalProvidersController.cs`  
(or add to existing admin controller)

| Method | Route | Purpose |
|--------|-------|---------|
| GET    | `/api/v1/admin/external-providers` | List all providers |
| GET    | `/api/v1/admin/external-providers/{id}` | Get one |
| POST   | `/api/v1/admin/external-providers` | Create + register scheme |
| PUT    | `/api/v1/admin/external-providers/{id}` | Update + re-register scheme |
| DELETE | `/api/v1/admin/external-providers/{id}` | Delete + remove scheme |

All endpoints require admin authorization. `ClientSecret` returned as `null` (write-only) on GET responses.

Request model: mirrors `ExternalProvider` fields; `ClientSecret` (plaintext) encrypted before persistence.

---

## Config Cleanup

After DB seed is verified:

1. Remove `ExternalProviders` list from `MagiqConfig`
2. Remove `ExternalProviders` from all `appsettings*.json` files  
3. Remove `ExternalProviders` property initialization from `MagiqConfig` ctor
4. Remove the static `foreach` loop in `ServiceCollectionExtensions.AddMagiqAuthentication`
5. Replace with call to `DynamicOidcRegistration.RegisterProviders(...)`

---

## Migration Path (zero-downtime)

1. Deploy DB migration (new table, no breaking changes)
2. Seed existing providers from config into DB (one-time script or startup task with idempotency guard)
3. Deploy code: startup loads from DB; config entries still present (belt-and-suspenders)
4. Verify all existing OIDC flows work
5. Deploy config cleanup (remove from appsettings)

---

## Files Changed / Created

| Action | File |
|--------|------|
| New | `src/MagiqAuth.Core/Domain/Configuration/ExternalProvider.cs` |
| New | `src/MagiqAuth.Data/Mapping/Configuration/ExternalProviderMap.cs` |
| New | `src/MagiqAuth.Services/Configuration/IExternalProviderService.cs` |
| New | `src/MagiqAuth.Services/Configuration/ExternalProviderService.cs` |
| New | `src/MagiqAuth.Web.Framework/Infrastructure/DynamicOidcRegistration.cs` |
| New | `src/MagiqAuth.Web.Framework/Infrastructure/IDynamicAuthSchemeService.cs` |
| New | `src/MagiqAuth.Web.Framework/Infrastructure/DynamicAuthSchemeService.cs` |
| New | `src/MagiqAuth.Api/Controllers/ExternalProvidersController.cs` |
| New | `scripts/2.1.0/add_external_providers_table.sql` |
| New | `scripts/2.1.0/seed_external_providers.sql` |
| Modify | `src/MagiqAuth.Core/Configuration/MagiqConfig.cs` — remove `ExternalProviders` |
| Modify | `src/MagiqAuth.Core/Configuration/ExternalProviderConfig.cs` — delete file |
| Modify | `src/MagiqAuth.Web.Framework/Infrastructure/Extensions/ServiceCollectionExtensions.cs` — replace static loop |
| Modify | `src/MagiqAuth.Web/appsettings.json` — remove `ExternalProviders` block |
| Modify | `src/MagiqAuth.Web/appsettings.Production.json` — remove `ExternalProviders` block |
| Modify | `src/MagiqAuth.Web/appsettings.Springbrook.json` — remove `ExternalProviders` block |
| Register DI | Wire `IExternalProviderService`, `IDynamicAuthSchemeService` in DI registrar |

---

## Out of Scope

- UI for managing providers (admin portal — separate ticket)
- Per-customer provider assignment UI
- Certificate/JWKS-based client auth (currently uses implicit flow)
