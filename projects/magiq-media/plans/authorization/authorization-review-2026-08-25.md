# Authorization — plan

_Opened 2026-08-26. Consumes `reviews/authorization/authorization-review-2026-08-25.md`._
_Both 🔴 blockers on the prod-readiness gate are in this workstream._

---

## Status

| Step | Finding | State |
|---|---|---|
| 0 | **Open question 1 — does `magiq-auth` issue meaningful roles?** | ☑ **Answered 2026-08-26. No.** See below — it changed the shape of everything after it |
| 1 | **X-11.31** — the five policy setters | ☑ **Closed 2026-08-26.** Guarded, tested, documented. **Not built or run — no .NET SDK was available in the session** |
| 2 | **X-11.30** — the authorization layer proper | ☐ Open. 81 commands, 61 HTTP-reachable. **Blocked on step 0's answer landing in `magiq-auth`** |
| 3 | **X-11.34**, **X-11.35** | ☐ Open. Both **verified against code 2026-08-26** — see *What verification changed* |
| 4 | **X-11.23** — unreachable 403 declarations | ☑ **Closed 2026-08-26.** Declaration deleted from both download endpoints; no check added |

---

## Step 0 — the answer, and why it matters more than it looks

**`magiq-auth` issues no `roles` claim and no `actor_type` claim.** Verified by reading the source at
`D:\source\github\magiq-auth` on 2026-08-26, not from documentation.

`UserProfileService` — the only registered `IProfileService` — emits a fixed six-claim set
(`ClaimTypes.Name`, `TenantId`, `GivenName`, `Surname`, `LoginID`, `ClientName`) and no role of any
kind. Three further things independently block it even if it did: `ApiScopes` is an **empty array** and
there is no `ApiResource` anywhere, so `RequestedClaimTypes` is empty; no client's `AllowedScopes` goes
beyond `openid`/`profile`/`offline_access`; and **roles do not exist as data** — no role entity, no
table, no seeding, no assignment. A case-insensitive search for `role` across the domain, data and
services projects returns zero matches.

### Three consequences the review could not have anticipated

1. **The review's hope that "the stopgap and the real fix may be the same thing" is false.** It rested
   on roles existing. A `actor.Roles.Contains(...)` check compiles and runs today and admits nobody, so
   it is not a working stopgap — it is an inert one.

2. **`actor_type` is not issued either, which the review did not raise at all.** The platform's claims
   mapper defaults it to `"User"` when absent, so **`ActorType` is always `"User"` over HTTP**. That
   quietly changes the meaning of two guards already in the code: `AssetOwnership.CheckOwner` and
   `ForceReleaseCheckout` both read *"System **or** owner"*, and over HTTP the System half is dead.
   They are owner-only in practice. **This does not change the rule that they must not be deleted** —
   it makes it more important, because they are narrower than they read, not wider.

3. **A System-only interim guard is a hard HTTP lockout, not a restriction.** Anything gated on System
   is reachable only from a System context — in practice the operator CLI, whose console host resolves
   `Actor.System` when no actor is set.

### The decision taken

**Assume `magiq-auth` will issue roles to standard practice, and write the guard against roles now.**
Chase, 2026-08-26. So the interim guard is *System **or** `MediaAdministrator`*: the System branch keeps
the CLI and the profile seeder working today, the role branch is written and tested and starts
admitting people the moment the identity provider emits the claim, with no change on this side.

**The hand-off is written:** `docs/spec/shared/magiq-auth-role-claims-requirements.md` in the app repo —
what to issue, the four specific reasons nothing arrives today with file and line references, an ordered
list of what to build, and two empirical acceptance checks. **It needs sending to the `magiq-auth`
team.** Until it lands, the role branch admits nobody and the five commands are CLI-only.

---

## Step 1 — X-11.31, closed

**`ProfileGovernanceAuthorization.CheckPrivileged`** — new, in
`Catalog.WriteModel/Commands/MediaProfiles/Shared/`. System actor **or** the `MediaAdministrator` role,
case-insensitive, null-safe, fails closed. Wired into all five handlers: `SetCheckoutPolicy`,
`SetReviewPolicy`, `SetChangeRequestPolicy`, `SetCapabilities`, `SetAutoSubmitOnComplete`.

Refuses with `403` / `errorCode: TenantAdministratorRequired` — a new code, added to the cross-cutting
error catalog. Deliberately not `NotResourceOwner`: that would imply an owner exists whose credentials
would work, and `MediaProfile.OwnerId` is provenance.

**The check runs before the profile is read**, so a refusal does not disclose whether a profile id
exists. The tests enforce that with a `MockBehavior.Strict` repository carrying no setups — moving the
check below the load makes them fail.

### What verifying the premises changed

**The escalation was three commands, not one.** The setters write to the profile's *draft*;
`EditSessionGuard` reads `profile?.CheckoutPolicy` off the **published** profile. The real path was
`CreateMediaProfileRevision` → `SetCheckoutPolicy(None)` → `PublishMediaProfile`, and the first and
third are still unguarded under X-11.30.

Guarding the middle step is nonetheless **sufficient**, and it is worth knowing why rather than
assuming it: `MediaProfileDraft.FromPublished` copies the current policies into a new draft, so a
revision nobody can change the policy on republishes the same policy. Had the draft reset to defaults
instead, guarding the five setters would have closed nothing.

**Seeding is unaffected.** `SeedDefaultProfilesService` dispatches four of the five, and it runs from
the CLI, where `ConsoleExecutionContextAccessor` resolves `Actor.System`. Confirmed rather than assumed.

**No integration test touches these five endpoints**, so nothing there needed changing. The four
existing handler unit-test files now pass `TestCommandContext.ForSystem()` — a new helper mirroring the
one Registration already has — instead of a bare mock whose `Actor` is null.

### Not done

**Nothing was built or run.** The session had no .NET SDK and none could be installed. Every claim above
about behaviour is from reading source, not from a green test run. **`dotnet build` and
`dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/` before this goes near a PR.**

---

## Step 2 — X-11.30, the layer proper

Unchanged from the review except in size: **81 commands, 61 HTTP-reachable**, the five setters having
come off the list. Open questions 2–5 in the review are still open and still gate the design.

**It is now also blocked on something outside this repo.** Any role-based design is unimplementable
until `magiq-auth` issues the claim, which makes the hand-off document step 2's critical path rather
than a side errand. Two groups need a role and have no owner to fall back on — Metadata's 17 commands
and MediaProfile's remaining 13 — so they cannot be done in any other shape.

The parts that do **not** wait: Registration's five decision commands could take a System-actor gate
today, and `ApproveAmendment`'s own doc comment already promises one. Worth doing as its own small
change if step 2 stalls on the identity provider.

---

## Step 3 — X-11.34 and X-11.35, verified

Both were verified against source on 2026-08-26 before any work was planned on them. **Both hold**, and
the verification found more than the findings claimed.

### X-11.34 — true, with one correction and one refinement

The three handlers do not derive from `MediaItemGuardedCommandHandler`; `RequestPublication`, `Archive`
and `Withdraw` contain no actor check; and the open session really is closed underneath the holder —
`EditSessionCloseReason.Submitted` on publish, `Superseded` on archive and withdraw.

- **Correction: "silently" is only half right.** An `EditSessionClosed` domain event is emitted,
  persisted, published to SNS and projected by three projectors, so it is fully auditable. What is
  absent is any user-facing notification, and on the archive path `closedBy` is `null` — the audit
  record does not name who broke the lock.
- **Refinement: withdraw partially restores the lock and archive never does.** `Withdraw` reopens the
  session, but only when the item was `PendingApproval`, and from the review roster rather than the
  session. Withdrawing a `Published` or `Revising` item destroys the lock outright.
- **New, and cheap: the archive endpoint documents a guard that does not exist.**
  `ArchiveMediaItemEndpoint` declares *"Cannot archive while checked out"* and a 422 for *"already
  archived or checked out"*. Nothing checks it. That is a doc fix that rides along with whatever PR
  touches the file.
- `ArchiveMediaItemCommand` carries **no `RequestingUser` at all**, so guarding archive means changing
  the command shape, not just adding a line.

### X-11.35 — true on every clause, and the undetermined one resolves badly

`AssignToFolder` guards only `FolderId.HasValue`; `Move` guards only "is assigned" and "not the same
folder". Neither command carries an actor at all, so `EditSessionGuard` could not be called without
changing the command shape.

**The "not determined" question is now determined.** `ArchiveMediaItemHandler` releases the title
reservation, and `Apply(MediaItemArchived)` does **not** clear `FolderId` — so an archived item still
passes `Move`'s gate with its reservation row gone. The DynamoDB store's delete leg carries
`ConditionExpression = "OwnerId = :oid"`, which fails on a missing item, and the handler converts the
resulting exception into **`409 "A media item with this title already exists in the destination
folder."`** So: not a silent no-op, not an upsert — a **permanently unactionable 409 blaming a title
conflict that does not exist**, indistinguishable from a real one to any client.

**And a latent test gap worth its own line:** the in-memory reservation store *upserts* in the same
scenario instead of throwing. Any test written against it will pass where DynamoDB fails.

**Also:** `AssignMediaItemToFolderHandler` auto-submits for publication as `owner_system` after its own
save, without inspecting the dispatch result — so a failed inner publish leaves the item assigned,
unpublished and uncompensated while the outer call returns success. And because it dispatches
`PublishMediaItemCommand`, **a folder assignment can transitively terminate another user's checkout**
via X-11.34.

---

## Step 4 — X-11.23, closed

`.ProducesProblem(403)` and its summary line deleted from `GetAssetDownloadUrlEndpoint` and
`GetRenditionDownloadUrlEndpoint`. **No check added** — the absent owner check is the design.

Re-verified before removing: the only `Forbidden` in the whole AssetManagement module is
`AssetOwnership.CheckOwner` on the write side, and nothing maps a read-model query error to
`QueryErrorCode.Forbidden`. The claim in `asset.api.md` was updated to record the fix rather than the
finding. The remaining unreachable 403s across the API surface stay with **X-11.27**.

---

## The three rules, still standing

Restated because each survived contact with the work rather than being incidental to it:

1. **`AssetOwnership.CheckOwner` and `ForceReleaseCheckout`'s owner check were not touched.** Step 0
   made the case for keeping them stronger, not weaker — they are owner-only in practice, so they guard
   *less* than they read, and removing them ahead of the layer widens X-11.30.
2. **No owner check was spread as a mitigation.** The X-11.31 guard is authorization-shaped: System or
   a role.
3. **Nothing was built on `OwnerId`.** It was ruled out explicitly for the five setters — the default
   profiles carry `owner_system`, so an owner check there would have been inoperable as well as wrong
   by the ADR's test.

---

## Next

1. **Send the hand-off** — `docs/spec/shared/magiq-auth-role-claims-requirements.md` to the `magiq-auth`
   team. Step 2 waits on it.
2. **Build and test the X-11.31 change.** It has never been compiled.
3. **Decide open questions 2–5** in the review — they gate the shape of step 2 and none needs the
   identity provider to answer.
4. **Consider splitting out Registration's five decision commands** as a System-only change that does
   not wait on anything.

---

## Related

- `../../reviews/authorization/authorization-review-2026-08-25.md` — the review this consumes
- `../prod-readiness/prod-readiness-gate.md` — where these sit against a release
- `../spec-drift-review/spec-repo-drift-review.md` — X-11.23, 30, 31, 34, 35 in full
- `docs/spec/shared/authorization-matrix.md` (app repo) — the evidence base, updated 2026-08-26
- `docs/spec/shared/magiq-auth-role-claims-requirements.md` (app repo) — the hand-off
- `docs/adrs/ownership-and-authorization.md` (app repo) — the model and the admin test
