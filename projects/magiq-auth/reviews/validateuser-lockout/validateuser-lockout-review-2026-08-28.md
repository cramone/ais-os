---
id: MA-001
type: review
project: magiq-auth
workstream: validateuser-lockout
raised-by: []
status: draft
outcome: pending
todo-id: 3609542e-61e6-5b33-ae13-978a21c44c62
created: 2026-08-28
---

# ValidateUser Lockout — Review

Account lockout on `UserMembershipService.ValidateUser` is reachable by any unauthenticated caller and
is not recoverable by the affected user. This review argues the findings. **It does not carry the
design** — the remediation design already drafted in the source report is held for the plan.

## Scope

**Read**

- `src/MagiqAuth.Services/Users/UserMembershipService.cs` — `ValidateUser`, lockout branch
- All six `ValidateUser` call sites (table under VUL-6)
- `src/MagiqAuth.Web/Controllers/UserController.cs` — `PasswordResetSend`, `PasswordResetConfirmPOST`
- `src/MagiqAuth.Core/WebHelper.cs` — `GetCurrentIpAddress`
- `D:\source\github\magiq-auth\reports\ValidateUser-Lockout-Review.md` (2026-08-28) — the source
  analysis this review is adapted from. It remains the working artefact in the code repo; §§3–5, 7–8 of
  it are the proposed design and test/rollout plan, which belong in the plan, not here.
- `D:\source\github\magiq-auth\PRODUCTION_CODE_AUDIT_REPORT.md` — cross-referenced for VUL-9 only

**Not read / out of scope**

- IdentityServer4 client and grant configuration beyond `UserStore.ValidateCredentials`
- The Azure AD / external-IdP login path — federated logins do not reach `ValidateUser`
- Password policy, hashing and `GetCurrentPassword` correctness
- The future Openiddict/DynamoDB migration target. **This review is scoped entirely to the current
  deployed system.**

**Constraint carried from the source report:** remediation is expected to ship as a hotfix to production
— no interface signature changes, no enum renames, no controller response-shape changes, no schema
migration. That constraint shapes the plan; it does not soften any finding below.

## Findings

Finding ids are workstream-scoped with prefix `VUL-`. Severity is High / Medium / Low.

---

### VUL-1 — Any unauthenticated caller can permanently disable any account · **High**

**Evidence:** `src/MagiqAuth.Services/Users/UserMembershipService.cs:90–105`

```csharp
user.FailedLoginAttempts++;
if (_magiqConfig.Users.FailedPasswordAllowedAttempts > 0
    && user.FailedLoginAttempts >= _magiqConfig.Users.FailedPasswordAllowedAttempts)
{
    user.Active = false; // Lockout the current user.
    user.FailedLoginAttempts = 0;
}
```

The temporary-lockout path (`CannotLoginUntilDateUtc`) is commented out at
`UserMembershipService.cs:87–88` and `:96`; the surviving behaviour sets `Active = false`, which is
**permanent** and clears only by administrator action.

**Impact:** every login endpoint is `[AllowAnonymous]`. Knowing a target's email address — which is
their username, and is not secret — is sufficient to lock them out of every MAGIQ cloud application
indefinitely. This is a denial-of-service against a named user, available to anyone on the internet, on
production and on every white-label domain. No rate limit, no CAPTCHA, no IP gate stands in front of it.

---

### VUL-2 — A client holding a stale saved password locks its own user out · **High**

**Evidence:** same branch, `UserMembershipService.cs:92`. `FailedLoginAttempts++` is unconditional on
password mismatch. Nothing compares the submitted credential against previously-rejected ones.

**Impact:** a client that retries a saved credential — a background poller, a webview, the VSTO add-in,
a mobile app — burns one counter tick per retry and reaches lockout in seconds after a password change.
This is the failure mode actually observed in production, and it is indistinguishable at the service
layer from VUL-1. The same wrong password submitted N times is a stuck client; N *different* wrong
passwords is an attack. The code treats them identically.

---

### VUL-3 — A locked-out user receives no signal · **Medium**

**Evidence:** all six call sites translate every non-`Successful` `UserLoginResult` to `Unauthorized()`.
No `User.AccountLocked` entry exists in `MessageTemplateSystemNames`.

The blanket `Unauthorized()` is **correct** and must be preserved — differentiating "locked" from "wrong
password" in the response is an account-enumeration oracle. The gap is the absence of any *out-of-band*
channel: the user is told nothing, by any means, and neither is anyone who could act on it.

**Impact:** a locked user's only route is a support ticket. It also means VUL-1 is silent — an attacker
locking accounts generates no notification to the victim and no signal anyone is watching.

---

### VUL-4 — Password reset is blocked for exactly the users who need it · **High**

**Evidence:** `src/MagiqAuth.Web/Controllers/UserController.cs:646`

```csharp
if (user != null && user.Active && !user.Deleted)
```

`PasswordResetSend` refuses to issue a reset token when `Active == false`. VUL-1 sets `Active = false`.

**Impact:** the two findings compose into a deadlock. Lockout removes the account's own recovery path,
so recovery requires an administrator in every case — including the self-inflicted VUL-2 case, which is
high-volume. This is the finding that turns an annoyance into a support-load and availability problem,
and it is the one most cheaply fixed.

---

### VUL-5 — No IP is captured on the failure path · **Medium**

**Evidence:** `IWebHelper.GetCurrentIpAddress()` exists and works
(`src/MagiqAuth.Core/WebHelper.cs:118`) but is never called from any login path.

**Impact:** three consequences, in order of cost. There is no per-IP failure counter, so credential
stuffing and email enumeration across many accounts from one source are invisible. There is no way to
tell VUL-1 from VUL-2 after the fact — the forensic question "was this user attacked or is their client
stuck?" cannot be answered from what we store. And any throttle built later has no key to throttle on
beyond the email, which is attacker-controlled.

---

### VUL-6 — The lockout surface is duplicated across six call sites · **Medium**

**Evidence:**

| Caller | File | Line |
|---|---|---|
| IdentityServer credential validation | `src/MagiqAuth.Services/Authentication/UserStore.cs` | 209 |
| JWT V1 — `LoginCustomerInternal` | `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV1Controller.cs` | 123 |
| JWT V1 — `LoginCustomersInternal` | `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV1Controller.cs` | 276 |
| JWT V2 — `Login`, inline block | `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV2Controller.cs` | 85 |
| JWT V2 — `LoginCustomerInternal` | `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV2Controller.cs` | 292 |
| JWT V2 — `LoginCustomersInternal` | `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV2Controller.cs` | 418 |

**Impact:** any mitigation applied at the caller must be applied six times and stays correct only by
discipline. A seventh call site added later inherits none of it. This is a structural finding about
*where* the fix goes, not a defect in itself — but it is the reason a caller-side-only fix is fragile,
and the plan has to answer it explicitly.

---

### VUL-7 — `JwtAuthV2Controller.Login` validates credentials inside the `!ModelState.IsValid` branch · **High**

**Evidence:** `src/MagiqAuth.Web/Api/v1/Controllers/JwtAuthV2Controller.cs:81–85`

```csharp
if (!ModelState.IsValid)
{
    try
    {
        var loginResult = _userMembershipService.ValidateUser(model.Email?.ToLower(), model.Password, ...);
```

The credential check runs only when the model is **invalid**; a valid model falls through to
`LoginCustomersInternal`. Almost certainly an inverted condition.

**Impact:** this is in scope because it is a `ValidateUser` call site and it changes which lockout path
a V2 caller hits, but it is a correctness defect on the primary V2 login endpoint independent of
lockout. It plausibly warrants its own hotfix ahead of this workstream — see Open Question 3.

---

### VUL-8 — `Active = false` conflates "administrator disabled" with "locked by attempts" · **Medium**

**Evidence:** `UserMembershipService.cs:99` sets the same flag the admin UI sets. No discriminator
column, no `LockoutStatus`, no timestamp distinguishing the two.

**Impact:** the system cannot answer "is this account disabled on purpose?", so any automated unlock
risks re-enabling an account an administrator deliberately disabled. Reporting cannot separate lockout
volume from deliberate deactivation. Any fix must carry a discriminator, and — under the no-schema-change
constraint — it will have to be something other than a column.

---

### VUL-9 — Read-modify-write race on `FailedLoginAttempts` · **Medium**

**Evidence:** `UserMembershipService.cs:92` then `:102` — increment in memory, then `UpdateUser(user)`.
Not atomic. Concurrent failed attempts against one account across the two production EC2 nodes lose
increments. Already recorded in `PRODUCTION_CODE_AUDIT_REPORT.md` (Location 304, 863).

**Impact:** the lockout threshold is not the threshold under concurrency — it fires late, or not at all,
depending on interleaving. Low severity on its own; it matters here because any counter-based mitigation
inherits the same race unless the counter moves to an atomic store. **Ownership is genuinely ambiguous
between this review and the audit-remediation track** — see Open Question 2.

---

### VUL-10 — Polly retry wrapping is inconsistent across login methods · **Low**

**Evidence:** V1 `LoginCustomer` (`POST ""`) wraps its call in a retry policy; V1
`LoginCustomerInternal` does not. V2 is mixed.

**Impact:** none today — the policy fires on exception, and a wrong password returns a
`UserLoginResult` enum rather than throwing, so retries do not multiply attempt counts. It is recorded
because it is one refactor away from doing so, and because the inconsistency makes the login paths
harder to reason about as a set.

## Open Questions

1. **Valkey Serverless and multi-key reads.** `CLAUDE.md` records that the Redis/Valkey cache is
   Valkey-Serverless-compatible and therefore has no cross-slot multi-key operations. Any throttle
   keyed on email, IP, and (IP, email, password-hash) reads three key families in one decision. Does
   that need hash tags to co-locate slots, or separate round trips, or does it rule out Redis as the
   backing store for this? `sync-to-async-review-plan.md` already fixed a related `RemoveByPrefixAsync`
   N-round-trip problem — the same constraint applies here. **Open**

2. **Who owns VUL-9?** It is already in `PRODUCTION_CODE_AUDIT_REPORT.md` (Location 304, 863). Options:
   leave it there and have this review's plan depend on it, or pull ownership here because any
   counter-based mitigation is blocked on it. Minting the same defect in two registers is the outcome to
   avoid. **Open**

3. **Does VUL-7 split out?** It is a correctness bug on the main V2 login endpoint, unrelated to lockout
   except by location. Split into its own hotfix branch ahead of this workstream, or fold into this
   plan's first phase? **Open**

4. **Do per-IP thresholds survive NAT?** Local-government and enterprise customers egress through a
   single NAT address. A per-IP failure cap applied naively locks out an entire council on one shared
   address. Does the threshold need a per-tenant allowlist, a much higher per-IP ceiling, or a different
   key entirely (e.g. per-IP-per-email only)? **Open**

5. **Is the client IP resolvable on the IdentityServer path?** `UserStore.ValidateCredentials`
   (`UserStore.cs:209`) runs inside the IS4 grant pipeline. Does `IWebHelper.GetCurrentIpAddress()`
   return the real client address there, and behind the load balancer — i.e. is `X-Forwarded-For`
   honoured by the forwarded-headers configuration on all four environments plus the white-label
   domains? If not, VUL-5's mitigation silently keys everything to the LB address. **Open**

6. **Rollout scope.** Does this ship to all environments and all white-label customer domains at once,
   or production-first? Each white-label domain has its own MySQL database, so any per-database seeding
   step multiplies. **Open**

7. **Where do throttle and lockout events land?** New `LoginThrottled` / `LoginFailed` records are audit
   events, and `AuditLogging-Separation-Plan.md` is actively splitting `IAuditLogger` from diagnostics.
   Writing them to the old custom SQL-backed `ILogger` adds to the pile that plan is dismantling. Does
   this work wait on that split, target the new `IAuditLogger` before it lands, or use
   `IUserActivityService` as the source report proposes? **Open**

## Dependencies

No `depends-on` entries — this review has no unmet document dependency and can be worked now. The
following are **related documents** whose resolution feeds Open Questions rather than gating the review:

| Document | Location | Relationship |
|---|---|---|
| `PRODUCTION_CODE_AUDIT_REPORT.md` | code repo | Owns VUL-9 today (Location 304, 863). Ownership question — OQ 2. |
| `AuditLogging-Separation-Plan.md` | code repo | Governs where new login audit events land — OQ 7. |
| `sync-to-async-review-plan.md` | code repo | Established the Valkey Serverless multi-key constraint — OQ 1. |
| `ValidateUser-Lockout-Review.md` | code repo | Source analysis. Its §§3–5, 7–8 are the proposed design, to be lifted into the plan. |

**Legacy status.** All four predate this cycle. They carry no `id:` and no front-matter, so per the
`review-cycle` skill's § Legacy files their status is **UNKNOWN** — not met, not unmet. None of them is
listed in `depends-on` for that reason. If the plan needs a hard dependency on any of them, backfill
that one document with front-matter and an `MA-` id first.

**External blockers:** none.

## Recommended sequencing

Rough only — the plan refines this, and it assumes the hotfix constraint holds.

1. **VUL-4 first.** Relaxing the `PasswordResetSend` gate is a one-line change that restores a recovery
   path for every already-locked user. It is independently shippable, needs no new service, and reduces
   support load immediately. Ship it before anything else, even if the rest slips.
2. **VUL-7 next, or split out entirely** (OQ 3). It is small, it is a live correctness bug, and it
   changes the V2 code the later work edits — doing it first avoids rebasing over it.
3. **VUL-3 + VUL-8 together.** Notification needs a discriminator to know a lockout was attempt-driven
   rather than admin-driven, so the "how do we tell the two apart without a schema change" answer has to
   land with the notifier, not after it.
4. **VUL-5 then VUL-1/VUL-2.** IP capture is a prerequisite for any throttle, and is useful on its own as
   telemetry — it answers "how much of the current lockout volume is attack versus stuck client?" before
   thresholds are chosen. Landing it first turns OQ 4's threshold question from a guess into a
   measurement.
5. **VUL-1 and VUL-2 close together**, since one throttle addresses both, gated on OQ 1 and OQ 4.
6. **VUL-6 is a decision, not a phase** — resolve "caller-side or pushed down into the service" before
   step 5 is written, because it determines whether that work is one edit or six.
7. **VUL-9 and VUL-10 are followups**, subject to OQ 2. Neither blocks the hotfix.
