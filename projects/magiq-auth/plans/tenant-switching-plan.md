# Tenant Switching v2 — OIDC Token Exchange + Cookie Switch + Audit

**Branch base:** `develop`
**Supersedes:** `tenant-switching-plan.md` (this doc folds it in + closes gaps found in review: id_token claim parity, audit logging, and clarifies relationship to the existing `/api/v2/auth/switch` cookie endpoint)
**Goal:** Two parallel, non-overlapping tenant-switch mechanisms for two different client shapes:

1. **Cookie-based web session switch** (existing, branch `features/chase/tenant-switching-v1`) — `POST /api/v2/auth/switch`, Bearer JWT in, new JWT + rewritten MAGIQ/Perf/Doc cookies out. Used by browser-session clients (web portal, embedded webviews hitting other MAGIQ Cloud apps that only check cookies, not OIDC).
2. **OIDC-native token exchange switch** (new, RFC 8693) — `POST /connect/token` with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`. Used by headless/bearer-only OIDC clients (VSTO Office add-in, any future API client holding only access/refresh tokens, no cookie jar).

Neither replaces the other. A client that needs both (e.g. VSTO add-in that also opens an embedded browser to a cookie-checking MAGIQ app) needs to call both endpoints.

---

## Scope Summary

| Capability | Approach | Branch | Status |
|---|---|---|---|
| Web/cookie tenant switch | `POST /api/v2/auth/switch`, Bearer JWT, cookie rewrite | `features/chase/tenant-switching-v1` | Already built — out of scope here, referenced only |
| VSTO login | Auth Code + PKCE via WebView2 | `feat/vsto-app-registration` | New |
| Refresh token rotation | IS4 `refresh_token` grant, rotation flag per-client | `feat/vsto-app-registration` | New |
| OIDC tenant switch | RFC 8693 token exchange custom grant | `feat/token-exchange-grant` | New |
| id_token claim parity | Ensure `tenant_id` lands in id_token, not just access_token | `feat/token-exchange-grant` | New (gap fix) |
| Audit logging | Log every switch (who/from/to/when) for both mechanisms | `feat/token-exchange-grant` + small patch to v1 switch endpoint | New (gap fix) |
| Custom JWT endpoints | Untouched | n/a | Out of scope |

---

## Branch 1 — VSTO App Registration + PKCE + Refresh Token Rotation

**Branch:** `feat/vsto-app-registration`
**PR target:** `develop`

### 1.1 — Add `RefreshTokenRotation` flag to `AppRegistration` entity

File: `src/MagiqAuth.Domain/Authentication/AppRegistration.cs`

```csharp
public bool RefreshTokenRotation { get; set; }
```

Migration: `migrations/mysql/006_AddRefreshTokenRotation.sql`
```sql
ALTER TABLE AppRegistrations ADD COLUMN RefreshTokenRotation TINYINT(1) NOT NULL DEFAULT 0;
```
(Use repo's numbered-migration convention, MySQL syntax — not the SQL Server `IF NOT EXISTS`/`BIT` from the v1 draft.)

### 1.2 — Wire rotation flag in `MagiqClientStore`

File: `src/MagiqAuth.Services/Authentication/MagiqClientStore.cs`

In `CreateClientForAppRegistration()`, `CreateClientForApplicationWithTenantContext()`, `CreateClientForCustomer()` — after `AllowOfflineAccess = true`:

```csharp
RefreshTokenUsage = appRegistration.RefreshTokenRotation
    ? TokenUsage.OneTimeOnly
    : TokenUsage.ReUse,
UpdateAccessTokenClaimsOnRefresh = appRegistration.RefreshTokenRotation,
```

**Why:** scoped to new VSTO client only — existing clients keep `ReUse` default, no breaking change.

### 1.3 — Seed VSTO `AppRegistration` in DB

`migrations/mysql/007_SeedVstoAppRegistration.sql` — operator reviews ClientId/RedirectUris before running in each customer environment:

```sql
INSERT INTO AppRegistrations (
    ClientId, Name, RequirePkce, AllowPlainTextPkce,
    RedirectUris, PostLogoutRedirectUris, RefreshTokenRotation
)
VALUES (
    'magiq-vsto', 'Magiq VSTO Office Add-in',
    1, 0,
    'http://localhost', 'http://localhost',
    1
);
```

Loopback `http://localhost` (no port) per RFC 8252 §7.3 — IS4 matches any port on localhost when redirect URI has no port specified.

### 1.4 — Verify IS4 allows port-agnostic localhost match

File: `src/MagiqAuth.Web.Framework/Infrastructure/Extensions/ServiceCollectionExtensions.cs`

Confirm no `StrictRedirectUriComparison` or custom `IRedirectUriValidator` breaking loopback. If a custom validator exists, ensure it passes `http://127.0.0.1:<any_port>` and `http://localhost:<any_port>`.

### Acceptance Criteria — Branch 1

- [ ] `AppRegistrations` has `RefreshTokenRotation` column
- [ ] `magiq-vsto` row seeded
- [ ] Auth Code + PKCE flow completes via Postman/curl against `/connect/authorize` → `/connect/token`
- [ ] `grant_type=refresh_token` issues new access token + new refresh token (rotation), old refresh token invalidated
- [ ] Existing clients (web, mobile) unaffected — refresh tokens still `ReUse`

---

## Branch 2 — RFC 8693 Token Exchange Grant (OIDC Tenant Switch)

**Branch:** `feat/token-exchange-grant`
**PR target:** `feat/vsto-app-registration` (depends on Branch 1) or `develop` if shipped independently

### 2.1 — Implement `IExtensionGrantValidator`

New file: `src/MagiqAuth.Services/Authentication/TokenExchangeGrantValidator.cs`

```csharp
public class TokenExchangeGrantValidator : IExtensionGrantValidator
{
    public string GrantType => "urn:ietf:params:oauth:grant-type:token-exchange";

    private readonly ITokenValidator _tokenValidator;
    private readonly IUserRepository _userRepository;
    private readonly ICustomerRepository _customerRepository;
    private readonly IActivityLogService _activityLogService; // gap fix: audit
    private readonly IHttpContextAccessor _httpContextAccessor;

    public async Task ValidateAsync(ExtensionGrantValidationContext context)
    {
        var subjectToken = context.Request.Raw.Get("subject_token");
        var subjectTokenType = context.Request.Raw.Get("subject_token_type");
        var requestedTenant = context.Request.Raw.Get("requested_tenant"); // customer GUID or name

        if (subjectTokenType != "urn:ietf:params:oauth:token-type:access_token")
        {
            context.Result = new GrantValidationResult(TokenRequestErrors.InvalidRequest,
                "subject_token_type must be access_token");
            return;
        }

        var validationResult = await _tokenValidator.ValidateAccessTokenAsync(subjectToken);
        if (validationResult.IsError)
        {
            context.Result = new GrantValidationResult(TokenRequestErrors.InvalidGrant,
                "subject_token invalid or expired");
            return;
        }

        var subjectId = validationResult.Claims
            .FirstOrDefault(c => c.Type == JwtClaimTypes.Subject)?.Value;

        var user = await _userRepository.GetByIdAsync(Guid.Parse(subjectId));
        var customer = await _customerRepository.GetByGuidOrNameAsync(requestedTenant);

        if (customer == null || !await _userRepository.UserHasAccessToCustomerAsync(user.Id, customer.Id))
        {
            // gap fix: log failed attempt too — tenant enumeration signal
            await _activityLogService.LogTenantSwitchAttemptAsync(
                userId: user?.Id, fromTenant: null, toTenant: requestedTenant,
                success: false, mechanism: "token-exchange",
                ip: _httpContextAccessor.HttpContext?.Connection.RemoteIpAddress?.ToString());

            context.Result = new GrantValidationResult(TokenRequestErrors.InvalidGrant,
                "User does not have access to requested tenant");
            return;
        }

        var fromTenantClaim = validationResult.Claims
            .FirstOrDefault(c => c.Type == "tenant_id")?.Value;

        var claims = new List<Claim>
        {
            new Claim("tenant_id", customer.Guid.ToString()),
            new Claim("customer_name", customer.Name),
        };

        // gap fix: audit successful switch
        await _activityLogService.LogTenantSwitchAttemptAsync(
            userId: user.Id, fromTenant: fromTenantClaim, toTenant: customer.Guid.ToString(),
            success: true, mechanism: "token-exchange",
            ip: _httpContextAccessor.HttpContext?.Connection.RemoteIpAddress?.ToString());

        context.Result = new GrantValidationResult(
            subject: subjectId,
            authenticationMethod: GrantType,
            claims: claims
        );
    }
}
```

`IActivityLogService.LogTenantSwitchAttemptAsync` — new method (or reuse existing `ActivityLog` table/service if one already logs auth events; check `MagiqAuth.Services` for existing `IActivityLogService` before adding a new one). Writes: userId, fromTenant, toTenant, success bool, mechanism string (`"token-exchange"` vs `"cookie-switch"` — see Branch 3), timestamp, source IP.

### 2.2 — Fix id_token claim parity (gap from v1 review)

IS4's extension grant pipeline by default only shapes the **access_token** via `GrantValidationResult.Claims` — it does not automatically emit an id_token for a non-interactive grant unless the client requests the `openid` scope and IS4 is configured to issue one for extension grants.

Action:
- In `CreateClientForAppRegistration()` (or wherever VSTO client scopes are set), confirm `AllowedScopes` includes `openid` and that the token endpoint response for this grant type includes an `id_token`.
- If IS4 doesn't emit id_token for extension grants by default in this version, add `IdentityTokenLifetime` consideration and verify via integration test that `id_token` in the token response carries `tenant_id` — not just `access_token`.
- If downstream VSTO UI (or any consumer) reads tenant context from id_token rather than access_token, this must not silently diverge. Add explicit assertion in acceptance criteria below.

### 2.3 — Register the grant validator

File: `src/MagiqAuth.Web.Framework/Infrastructure/Extensions/ServiceCollectionExtensions.cs`

```csharp
idsBuilder.AddExtensionGrantValidator<TokenExchangeGrantValidator>();
```

```csharp
services.AddTransient<TokenExchangeGrantValidator>();
```

### 2.4 — Allow the grant type on VSTO client

Add property to `AppRegistration`:
```csharp
public bool AllowTokenExchange { get; set; }
```

Migration: `migrations/mysql/008_AddAllowTokenExchange.sql`
```sql
ALTER TABLE AppRegistrations ADD COLUMN AllowTokenExchange TINYINT(1) NOT NULL DEFAULT 0;
```

In `CreateClientForAppRegistration()`:
```csharp
AllowedGrantTypes = appRegistration.AllowTokenExchange
    ? GrantTypes.Code.Concat(new[] { "urn:ietf:params:oauth:grant-type:token-exchange" }).ToList()
    : GrantTypes.Code,
```

Update VSTO seed:
```sql
UPDATE AppRegistrations SET AllowTokenExchange = 1 WHERE ClientId = 'magiq-vsto';
```

### 2.5 — Token exchange request (VSTO usage)

```http
POST /connect/token
Content-Type: application/x-www-form-urlencoded

client_id=magiq-vsto
&grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&subject_token=<current_access_token>
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Aaccess_token
&requested_tenant=<customer-guid-or-name>
```

Response: standard IS4 token response, new `access_token` (and `id_token` per 2.2 fix) scoped to requested tenant.

### 2.6 — Security considerations

- Subject token must be valid and non-expired (validator checks)
- User must have explicit access to requested tenant (checked against same `UserCustomer` membership table used by existing auth — same check as `/api/v2/auth/switch` and `MultitenantApiClientTokenValidator`)
- Issued token lifetime matches standard access token lifetime (not separately configurable)
- Refresh token NOT issued for exchanged tokens — client holds original refresh token, re-exchanges after access token expiry
- Rate limit token exchange per client per minute — prevents tenant-enumeration brute force (add middleware or rate-limit attribute on `/connect/token` scoped to this grant type)
- All attempts (success + failure) audit-logged per 2.1

### Acceptance Criteria — Branch 2

- [ ] `POST /connect/token` with `grant_type=token-exchange` returns 400 for unknown/invalid subject token
- [ ] Returns 400 when user does not have access to requested tenant
- [ ] Returns 200 with new access token containing `tenant_id` claim for valid request
- [ ] Returns 200 with new **id_token** also containing `tenant_id` claim (gap-fix verification)
- [ ] Existing `/connect/token` flows (code, refresh_token, client_credentials) unaffected
- [ ] Token exchange not permitted on clients without `AllowTokenExchange = true`
- [ ] Successful and failed switch attempts appear in activity log with correct from/to tenant, user, mechanism

---

## Branch 3 — Audit Logging Parity for Cookie Switch (small patch, not a rebuild)

**Branch:** `feat/tenant-switch-audit-logging`
**PR target:** `features/chase/tenant-switching-v1` (or `develop` if v1 already merged by the time this lands)

The existing `POST /api/v2/auth/switch` endpoint (built in `features/chase/tenant-switching-v1`) does not currently audit-log switch events. Add the same `IActivityLogService.LogTenantSwitchAttemptAsync` call (mechanism: `"cookie-switch"`) at the point the endpoint resolves target `UserCustomer` and rewrites cookies, mirroring 2.1's call shape. No change to cookie-rewrite logic, JWT shape, or claims — this is purely the audit-log gap fix called out in plan review.

### Acceptance Criteria — Branch 3

- [ ] Successful `/api/v2/auth/switch` calls produce an activity log row (userId, fromTenant, toTenant, success=true, mechanism="cookie-switch")
- [ ] Failed switch attempts (membership check fails) also logged with success=false
- [ ] No behavior change to existing cookie-switch response shape or JWT claims

---

## End-to-End VSTO Flow (Post-Implementation)

```
1. INITIAL LOGIN
   VSTO opens WebView2 → GET /connect/authorize
     ?client_id=magiq-vsto
     &response_type=code
     &redirect_uri=http://localhost:<port>
     &scope=openid profile offline_access
     &code_challenge=<S256-hash>
     &code_challenge_method=S256

   User logs in (2FA handled in WebView2 browser UI)
   IS4 redirects → http://localhost:<port>?code=<auth_code>
   VSTO catches redirect → POST /connect/token (code + code_verifier)
   Store: access_token (short-lived) + refresh_token (DPAPI encrypted)

2. SILENT REFRESH
   Access token near expiry → POST /connect/token
     grant_type=refresh_token
     refresh_token=<stored>
     client_id=magiq-vsto
   → new access_token + new refresh_token (old refresh token invalidated)
   Update DPAPI store with new refresh_token

3. TENANT SWITCH (headless, OIDC-native)
   User selects different customer in add-in UI → POST /connect/token
     grant_type=urn:ietf:params:oauth:grant-type:token-exchange
     subject_token=<current_access_token>
     subject_token_type=urn:ietf:params:oauth:token-type:access_token
     requested_tenant=<customer-guid>
     client_id=magiq-vsto
   → new access_token + id_token, both with tenant_id claim for selected customer
   (no WebView2, no user prompt, fully headless)
   → activity log row written (mechanism=token-exchange)

4. IF VSTO ALSO EMBEDS A COOKIE-CHECKING MAGIQ APP VIEW
   Separately call POST /api/v2/auth/switch with current Bearer JWT
   → cookies (MAGICookie-{Id}, PerfCookie, DocCookie, DocTicket) rewritten for new tenant
   → activity log row written (mechanism=cookie-switch)
   Both calls needed — token exchange does not touch cookies, cookie switch does not touch OIDC tokens
```

---

## Migration Scripts Summary

| Script | Purpose |
|---|---|
| `migrations/mysql/006_AddRefreshTokenRotation.sql` | Add `RefreshTokenRotation` column to `AppRegistrations` |
| `migrations/mysql/007_SeedVstoAppRegistration.sql` | Seed VSTO client row |
| `migrations/mysql/008_AddAllowTokenExchange.sql` | Add `AllowTokenExchange` column |
| (Branch 3) no schema change — reuses existing `ActivityLog` table if present, else add minimal columns for mechanism/fromTenant/toTenant |

---

## Out of Scope

- Changes to `/api/v1/auth` JWT shape or cookie-switch business logic itself (Branch 3 only adds logging, not behavior change)
- Changes to web or mobile client configurations
- Admin UI for managing `AppRegistration` flags (manual DB or existing admin tooling)
- Token exchange refresh token issuance (by design — client re-exchanges using original refresh token after access token expiry)

---

## Open Questions for Implementer

1. Does an `IActivityLogService` (or equivalent) already exist in `MagiqAuth.Services` that logs auth events to the `ActivityLog` table? If yes, extend it rather than adding a new service — check before writing 2.1/Branch 3.
2. Does IS4 (as currently configured in this repo's IdentityServer4 version) emit `id_token` for extension grant responses by default, or does `AllowedScopes`/`AlwaysIncludeUserClaimsInIdToken` need explicit configuration? Verify via integration test before relying on 2.2.
3. Does the VSTO add-in need an embedded view into any cookie-checking MAGIQ app (Springbrook/Caselle/etc)? If yes, Branch 3's audit fix aside, the VSTO client also needs to call `/api/v2/auth/switch` per the Branch 4 flow step above — confirm with VSTO product owner before considering tenant-switch "done" for that client.
