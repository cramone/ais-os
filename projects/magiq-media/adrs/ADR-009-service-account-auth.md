# ADR-009: Service Account Authentication — Client Credentials + JTI Replay Exemption for System Actors

**Status:** Accepted  
**Date:** 2026-05-21  
**Deciders:** Chase Ramone

---

## Context

The platform needs to support non-interactive clients — specifically a CLI tool and a backend integration service — that authenticate against the Media.Api without a human login flow. These clients require a durable, headless credential mechanism.

Additionally, the existing JWT replay detection model (`media-used-jtis` table) was designed with browser-based User sessions in mind. As specced, every authenticated request records the token's `jti` in DynamoDB and rejects any subsequent request presenting the same `jti`. This makes every token effectively single-use, which is incompatible with the access pattern of a backend service or CLI making multiple API calls per session.

**Actor type in question:** `System` — internal service or automated process. Entitled to invoke privileged commands (`ForceReleaseCheckout`, system-dispatched `ApproveMediaItem`, etc.).

---

## Decision

### 1. Client Credentials Grant for Service Account Token Issuance

CLI tools and backend services authenticate to the Identity provider (upstream context) via the **OAuth 2.0 Client Credentials grant** (`grant_type=client_credentials`). The Identity provider issues a short-lived JWT with the following required claims:

| Claim | Value |
|---|---|
| `actor_type` | `"System"` |
| `tenant_id` | Tenant the service account belongs to |
| `sub` | Stable, unique service principal identifier (e.g., `system_cli-ingest`) |
| `name` | Human-readable service name |
| `roles` | Roles granted to the service account (may be empty or scoped) |
| `exp` | Short TTL — 15 minutes recommended |
| `jti` | UUID v4, unique per token issuance |

Credentials (`client_id` + `client_secret`) are stored:

- **CLI:** `~/.magiq/credentials` (mode `0600`), populated on first-run `magiq auth login --service-account`. Environment variable override (`MAGIQ_CLIENT_ID` / `MAGIQ_CLIENT_SECRET`) for CI/CD contexts.
- **Backend service:** AWS Secrets Manager. Read at cold start; re-read on `401` response to handle rotation. Rotation is handled by a Secrets Manager rotation Lambda — the service does not manage key rotation itself.

The CLI caches the issued token locally (in-memory per invocation; on-disk cache optional) and re-authenticates when `exp - 30s` is reached.

### 2. JTI Replay Detection — System Actors Exempted

`actor_type = "System"` tokens are **exempt from JTI recording and replay checks**.

The `HttpExecutionContext` JTI middleware skips the `media-used-jtis` `GetItem` / `PutItem` cycle when `actor_type = "System"`. The check still runs unconditionally for `User` actors.

Short-lived tokens (15-minute TTL) combined with automatic rotation via client credentials re-auth are the primary protection mechanism for System tokens. A System actor that loses a token has a maximum 15-minute exposure window.

---

## Alternatives Considered

### A. Single-use tokens for System actors (enforce existing JTI model)

Would require the Identity provider to issue a fresh token **per API request**. This is impractical:

- Every API call incurs an additional round-trip to the Identity provider.
- At 500 req/s (System tier rate limit), this saturates the auth layer.
- Client credentials grant is not designed for per-request issuance.

**Rejected.**

### B. Scoped JTI check — record JTI only on revocation (revocation list pattern)

Replace the "record on first use" model with an explicit revocation list. JTIs are only written to `media-used-jtis` when a token is actively revoked (key rotation, incident response). All requests proceed unless the JTI appears in the revocation list.

This is the correct long-term architecture and aligns with standard JWT revocation practice. It preserves replay protection for User tokens without penalising System tokens.

**Not chosen now** — requires a revocation endpoint and operational runbook. Deferred to a future ADR. The current decision (exemption by actor type) is an acceptable interim position because:

1. System tokens have a short TTL (15 min).
2. System credentials are stored in Secrets Manager with rotation — the blast radius of a leaked credential is bounded.
3. System endpoints are not callable by User actors regardless (enforced by `RequireActorType("System")` FastEndpoints policy).

### C. Device Authorization Grant (CLI)

Appropriate when the CLI operator is a human user (`actor_type = "User"`). Not applicable here — the use case is a service account acting autonomously, not on behalf of a specific user.

---

## Consequences

**Positive:**
- CLI and backend service can authenticate without human interaction.
- Token lifecycle is well-understood (client credentials → short-lived JWT → re-auth on expiry).
- System-tier rate limits (500 req/s, 1000 burst) are not impacted by per-request auth overhead.
- `actor_type = "System"` enforcement at FastEndpoints policy layer remains unchanged — this ADR only affects replay detection, not endpoint access control.

**Negative / Accepted trade-offs:**
- System tokens do not benefit from replay detection. A stolen System token is valid until `exp`. Mitigated by the 15-minute TTL and Secrets Manager rotation.
- The JTI exemption is conditional on `actor_type` claim, which is identity-provider-issued and not independently verifiable by the API without trusting the issuer. This is the same trust boundary as all other JWT claims — acceptable.
- A future revocation list ADR is now load-bearing: if a System credential is compromised, the current tooling supports only waiting out the TTL or rotating the client secret (which invalidates future tokens but not in-flight ones).

---

## Implementation Notes

**JTI middleware configuration:**

The middleware exposes a `BypassPredicate` on `JtiReplayDetectionOptions` that receives the resolved `ClaimsPrincipal` and returns `true` to skip replay detection for that request. Wire it in `Media.Api` startup:

```csharp
builder.Services.Configure<JtiReplayDetectionOptions>(options =>
{
    options.BypassPredicate = principal =>
        principal.FindFirstValue("actor_type") is "System";
});
```

The predicate is evaluated after JWT signature validation — the `ClaimsPrincipal` is fully authenticated at that point. The `media-used-jtis` `GetItem` / `PutItem` cycle is skipped entirely when the predicate returns `true`.

**CLI token management (sketch):**

```csharp
public async Task<string> GetAccessTokenAsync(CancellationToken ct)
{
    if (_cachedToken is not null && _cachedToken.ExpiresAt > DateTimeOffset.UtcNow.AddSeconds(30))
        return _cachedToken.AccessToken;

    var credentials = _credentialStore.Load(); // reads ~/.magiq/credentials or env vars
    var token = await _identityClient.ClientCredentialsAsync(
        credentials.ClientId,
        credentials.ClientSecret,
        ct);

    _cachedToken = token;
    return token.AccessToken;
}
```

**CDK / Secrets Manager:**

The backend service's `client_id` and `client_secret` are provisioned as a single Secrets Manager secret (`/magiq-media/{env}/service-accounts/{service-name}`). The Lambda execution role is granted `secretsmanager:GetSecretValue` for that specific ARN. No other IAM principal has access.

---

## Related

- [system-spec.md — Authentication & Authorization](../spec/shared/system-spec.md#authentication--authorization)
- [system-spec.md — Token Replay Detection](../spec/shared/system-spec.md#token-replay-detection)
- [system-spec.md — Rate Limiting, System tier](../spec/shared/system-spec.md#tiers-by-actor-type)
- [security-scenarios.md — PERM-2 User Actor Calls System-Only Endpoint](../spec/shared/security-scenarios.md#perm-2-user-actor-calls-system-only-endpoint)
