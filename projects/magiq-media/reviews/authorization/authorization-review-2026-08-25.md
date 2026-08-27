# Authorization — the missing layer

_Opened 2026-08-25 from the spec-drift review (W22). **Both 🔴 blockers on the prod-readiness gate are
here.** The evidence is complete; this is execution, not investigation._

> ## Worked 2026-08-26 — the plan is `plans/authorization/authorization-review-2026-08-25.md`
>
> **X-11.31 and X-11.23 are closed.** X-11.34 and X-11.35 were verified against source and both hold,
> with material additions recorded in the plan. X-11.30 is open and is now **81 commands, 61
> HTTP-reachable** — the five setters have come off the list.
>
> **Open question 1 is answered, and the answer inverts the assumption underneath it.** See the
> question's row below. This page is left as it was written otherwise; the plan carries what changed.

---

## The finding, in one paragraph

**86 of 132 write commands have no authorization check of any kind.** They execute for any authenticated
member of the tenant, and **66 are reachable over HTTP**. There is no endpoint-level authorization anywhere
in the system: **zero** calls to `Roles()`, `Permissions()`, `Policies()` or `Claims()` across all 146
endpoint classes. Both hosts define an `"AuthenticatedUser"` policy and neither applies it to anything.
Everything that is enforced is 20 handler guards and 12 aggregate guards, hand-written per command.

**Full evidence:** `docs/spec/shared/authorization-matrix.md` in the magiq-media repo — all 132 commands
classified, with what enforces each and where.
**The model:** `docs/adrs/ownership-and-authorization.md` — authorization vs domain standing vs provenance.

---

## Why X-11.31 comes first, and why it is not just "another gap"

**`EditSessionGuard` is the most widely applied guard in the system** — nine MediaItem commands run through
`MediaItemGuardedCommandHandler`. Its checkout half is conditional on `MediaProfile.CheckoutPolicy`.

**`SetCheckoutPolicy` has no authorization.** Any authenticated tenant member can set the policy to
not-required and **neutralise that guard tenant-wide, for every item on the profile**. `SetReviewPolicy`
does the same to the review gate; `SetChangeRequestPolicy` to the change-request gate.

> **This is privilege escalation, not a missing check.** It converts a caller with no privileges into one
> for whom the remaining guards no longer apply. Every other gap on this page is bounded by what that one
> command does; this one is unbounded, because it turns the guards off.

**Five handlers** — `SetCheckoutPolicy`, `SetReviewPolicy`, `SetChangeRequestPolicy`, `SetCapabilities`,
`SetAutoSubmitOnComplete`. Smallest change on the gate, largest effect.

---

## What the shape of the problem tells you

**Registration is the clearest signal.** Five of its eleven commands are guarded by
`RegistrationOwnership.CheckOwner` — and they are the ones an officer runs on their *own* filing: submit,
resubmit, amend, cancel, attach. **The five that *decide* a filing are unguarded:**

`ConfirmRegistration` · `RejectRegistration` · `ApproveAmendment` · `RejectAmendment` ·
`RecordRegistrationSubmission`

`ApproveAmendment`'s own doc comment promises a System-actor gate that was never implemented. For a
government records platform this is the inverse of what is needed.

**Catalog shows the same pattern differently.** Of MediaItem's 34 commands, the eleven that run through the
guard base class are all **content edits** — title, description, tags, metadata, asset roles. The
**lifecycle transitions are not guarded at all**: `PublishMediaItem`, `ArchiveMediaItem`,
`WithdrawMediaItem`, `DeleteMediaItem`, `PurgeMediaItemVersion`, `CheckOutMediaItem`.

**So the rule the codebase actually follows is: content edits are guarded, lifecycle transitions are not.**
Nobody chose that. It is what you get when guards are added per-command as each one is written.

---

## Findings in this workstream

| # | Severity | What |
|---|---|---|
| ☑ **X-11.31** | ~~🔴 Critical 🔒~~ | ~~The five policy setters disable the guards tenant-wide.~~ **Closed 2026-08-26** — System or `MediaAdministrator`, handler-side, fails closed, checked before the profile is read. The escalation turned out to be three commands (`CreateMediaProfileRevision` → setter → `PublishMediaProfile`); guarding the middle one closes it because a new draft *copies* the published policies |
| **X-11.30** | 🔴 Critical 🔒 | ~~86 of 132~~ **81 of 132** commands unguarded; ~~66~~ **61** HTTP-reachable. Now also blocked on `magiq-auth` for anything role-shaped |
| **X-11.34** | Med 🔒 | Publish / archive / withdraw work on an item another user holds checked out — the holder's session is closed underneath them as `Submitted` or `Superseded`, silently |
| **X-11.35** | High | Folder assignment and move are guarded by **nothing** — no status, archive or checkout check. An item can be moved while checked out, mid-review, or **while archived**. The archived case collides with the title reservation released at archive time |
| ☑ **X-11.23** | ~~Low, docs~~ | ~~Both download endpoints declare `403` which no code path can return.~~ **Closed 2026-08-26** — declaration and summary line deleted from both endpoints, no check added, `asset.api.md` updated |

---

## Rules that must survive this work

**1. Do not remove `AssetOwnership.CheckOwner` or `ForceReleaseCheckoutHandler`'s owner check.**

Both are *authorization wearing ownership's clothes* — by the ADR's test they fail, because an admin with
every permission should be able to do those things. But they are also, today, **the only guard on 8 asset
commands including the only route that destroys bytes**. Removing them ahead of an authorization layer
widens X-11.30 rather than cleaning anything up. **Replace in kind; never delete first.**

**2. Do not spread owner checks as a mitigation.**

The tempting move, given 86 gaps, is to add `actor.Id == aggregate.OwnerId` everywhere. That converts one
missing layer into 86 bespoke domain rules, **most of which fail the ADR's test**, and every one would need
unpicking later. A stopgap should be *authorization-shaped* — System-only, or a role check — not
ownership-shaped.

**3. `OwnerId` on Collection, Folder, MediaItem and MediaProfile is provenance.**

Decided 2026-08-25. It governs nothing and is being renamed `CreatedBy`. **Do not build authorization on
it.** `ChangeRequest.OwnerId` and `Registration.OfficerId` are the exceptions — those are genuine domain
standing and stay.

**4. Read access is tenant-scoped, and that is the design.**

No read endpoint has an owner check and none is intended; per-resource control lands with authorization.
Cross-tenant reads miss the projection key and return **404, not 403**, which is the right answer for a
boundary probe.

---

## Open questions

| # | Question |
|---|---|
| 1 | ~~**Does `magiq-auth` issue meaningful roles?**~~ ☑ **Answered 2026-08-26: no, and it issues no `actor_type` either.** The plumbing premise was right — `IActor.Roles` really is populated end to end, and a handler-side `Roles.Contains(...)` really does work with no framework. **The claim never arrives to populate it.** `UserProfileService` is the only `IProfileService` and emits six claims, none a role; `ApiScopes` is empty and no `ApiResource` exists, so `RequestedClaimTypes` is empty; no client allows a roles scope; and no role exists as *data* — zero matches for `role` across the domain, data and services projects. **So the hope in this row is false: a role check is not a working stopgap, it is an inert one.** Two knock-ons: `ActorType` is always `"User"` over HTTP, which makes `AssetOwnership.CheckOwner` and `ForceReleaseCheckout` owner-only in practice (they guard *less* than they read — another reason not to delete them); and anything gated on System is CLI-only. **Decision — Chase, 2026-08-26: write the guard against roles anyway**, so it starts working when the IdP catches up. Hand-off written: `docs/spec/shared/magiq-auth-role-claims-requirements.md`, **unsent** |
| 2 | Does authorization live in the platform SDK (`Magiq.AspNetCore`) or in this app? The SDK has `IPermissionService` / `IPermissionRequirement` already |
| 3 | Endpoint-level or handler-level? Endpoint-level is uniform and declarative; handler-level is where every existing check lives. Mixing is how this started |
| 4 | What is the tenant-admin concept? Several commands are tenant-wide configuration (all 17 Metadata, the profile lifecycle) with no owner at all — they need a role, not an owner |
| 5 | Do the four **dead** commands get guards or deletion? `AttachAssetToMediaItem`, `DetachAssetFromMediaItem`, `RejectMediaItem`, `UnlinkSigningSession`, `UpdateMediaItemConformanceStatus` are registered, unguarded, and dispatched by nothing |

---

## Sequencing

```
0. Answer open question 1 — does magiq-auth issue roles?
1. X-11.31 — five policy setters. Interim, explicitly marked as such
2. X-11.30 — the authorization layer proper
   · Metadata (17) and MediaProfile (18) need a role: no owner exists to check
   · Registration's five decision commands
   · Catalog lifecycle transitions
3. X-11.34, X-11.35 — fall out of 2, or are separate domain guards
4. X-11.23 — delete the unreachable 403 declarations
```

**Do not wait for step 0 to start step 1.** System-only on the five setters is correct regardless of what
roles turn out to exist, and it is reversible.

---

## Related

- `docs/spec/shared/authorization-matrix.md` — **the evidence base.** All 132 commands
- `docs/adrs/ownership-and-authorization.md` — the model and the *"would an admin still be bound?"* test
- `docs/spec/shared/multi-tenancy-and-auth.md` — claims, actor types, tenant resolution
- `docs/spec/shared/security-scenarios.md` § PERM-2 — the worked privileged-command scenario
- `plans/spec-drift-review/spec-repo-drift-review.md` — X-11.30, 31, 34, 35, 23 in full
- `plans/prod-readiness/prod-readiness-gate.md` — where these sit against a release
