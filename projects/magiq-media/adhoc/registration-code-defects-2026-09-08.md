# Registration — Code Defects and Open Decisions

_magiq-media · 2026-09-08 · Chase Ramone_

**What this file is.** The residue of the Registration spec ↔ repo drift review after the spec rewrite.
The 20 findings where the **spec** was wrong are gone — corrected in place on 2026-09-08. What remains is
the two categories the spec cannot fix by describing them:

- **§ 1 — Code defects (D-1…D-6).** The spec is right and the code is wrong.
- **§ 2 — Open decisions (U-1…U-5).** Spec and code disagree, or the code is unowned, and it is not
  obvious which should move.
- **§ 3 — Already owned elsewhere.** Two items that belong to existing workstreams; recorded so they are
  not re-raised here.

**Every row is marked in the spec.** Each carries the `file:line` of its `⚠` marker so the marker and the
work stay together — the spec tells a reader the behaviour is defective, this file tells you what to do
about it.

**Evidence** for every row is in
[`registration-spec-drift-2026-09-08.md`](./registration-spec-drift-2026-09-08.md), which keeps the full
`file:line` citations on both sides.

**Spec paths below are relative to** `D:\source\github\magiq-media\docs\spec\contexts\Registration\`.
**Code paths** are relative to `D:\source\github\magiq-media\src\`.

---

## 1. Code defects

### 1.1 Cross-context lifecycle

#### D-1 · A rejected registration loses its MediaItem link permanently · **High**

`RegistrationRejectedEventHandler` dispatches `RemoveRegistrationRefCommand`, which removes the
registration reference from the MediaItem **and** decrements its `active-registrations` counter.

But `Rejected` is not terminal. The lifecycle is `Rejected → Resubmitted → Submitted →
PendingConfirmation → Confirmed`, and **only `RegistrationInitiated` ever adds the reference**. Nothing
consumes `RegistrationResubmittedIntegrationEvent` or `RegistrationSubmittedIntegrationEvent` —
`EventConsumers/ConsumerRegistrations.cs:140-142` subscribes to exactly three Registration events:
initiated, rejected, cancelled.

**Two consequences after one reject → resubmit → confirm cycle:**

1. The MediaItem carries **no reference** to a registration that is confirmed and legally binding against
   it.
2. Its active-registration counter is one short, so **a Folder containing that item can be archived while
   the filing is live** — `ArchiveFolderHandler.cs:69` reads that counter to block exactly this.

| | |
|---|---|
| **Fix** | Preferred: stop Catalog unlinking on rejection — a rejection is a retry point, not an ending, and `RegistrationCancelled` already covers the terminal case. Alternative: consume `RegistrationResubmittedIntegrationEvent` in Catalog and re-add the ref, which is more moving parts and leaves a window where the counter is wrong |
| **Decide first** | Whether a rejected filing should count as "active" for Folder-archive purposes. The preferred fix says yes; the current code says no and then never recovers |
| **Code** | `modules/Catalog/Catalog.WriteModel/IntegrationEvents/Consuming/Handlers/RegistrationRejectedEventHandler.cs:33` · `modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RemoveRegistrationRef/RemoveRegistrationRefHandler.cs:32` |
| **Tests** | None cover the reject → resubmit → confirm path end to end. Add one that asserts the ref survives |
| **Marked in spec** | `aggregates/Registration/registration.scenarios.md:134` · `context-overview.md:114` |

### 1.2 Authorization

#### D-2 · `GET /v1/registrations?mediaItemId=` is tenant-scoped, not owner-scoped · **High**

`ListRegistrationsByOwnerQuery` filters on `OwnerId` taken from the execution context. The
`mediaItemId` branch does not: `ListRegistrationsByMediaItemQuery.Matches` filters on `TenantId` and
`MediaItemId` only, and `RegistrationByMediaItemIndexSchema` partitions on
`TENANT#{t}#ITEM#{mediaItemId}#REGISTRATIONS`.

So **any authenticated member of the tenant can enumerate every registration against any media item** —
including other officers' authority reference numbers — by supplying a `mediaItemId`. That is the same
hole closed on `/search` (owner `term` filter) and on the no-filter list path; this is the gap between
them.

| | |
|---|---|
| **Fix** | Depends on the decision below. If per-item listing is owner-scoped, add an `OwnerId` predicate and either accept the post-filter or add an owner component to the index. If it is meant to be shared, say so in the spec and leave the code |
| **Decide first** | **Is a registration's existence against a media item shared knowledge within the tenant?** A colleague browsing an item arguably should see it is registered. Seeing the *authority reference number* is a different question, and the summary row carries it |
| **Middle option** | Keep the list tenant-visible, drop `reference` from the summary projection on that path. Cheapest if the answer is "yes, but not the reference" |
| **Code** | `modules/Registration/Registrations.ReadModel/Queries/Registrations/ListRegistrationsByMediaItem/ListRegistrationsByMediaItemQuery.cs` · `Registrations.ReadModel.Endpoints/V1/Registrations/ListRegistrations/ListRegistrationsEndpoint.cs` |
| **Marked in spec** | `aggregates/Registration/registration.api.md:99` |

### 1.3 Dead code and inert fields

#### D-3 · The reference model writes `IsArchived` and nothing reads it · Medium

`MediaItemReference.IsArchived` is set to `true` by `MediaItemRegistrationIndexProjector` on
`MediaItemArchivedIntegrationEvent`. No handler reads it: `MediaItemRegistrationContextService` projects
only `IsPublished`, `HasRegistrationCapability`, `HasProcessingCapability` and `MediaProfileId` into
`MediaItemRegistrationContext`.

Harmless today, because the same handler also clears `IsPublished` and every guard tests that. But it is
the same shape as the `HasProcessingCapability` defect that survived undetected for months: a field
carried for a check nobody wired up.

| | |
|---|---|
| **Fix** | Drop the field, or surface it on `MediaItemRegistrationContext` and give it a guard with its own `errorCode`. Do not leave it written-and-unread |
| **Note** | If you keep it, the refusal for an archived item should probably not be `MediaItemNotPublished` — it is accurate but unhelpful, since republishing is not the remedy |
| **Code** | `modules/Registration/Registrations.WriteModel/IntegrationEvents/Consuming/ReferenceModels/MediaItemReference.cs:25` · `.../Projectors/MediaItemRegistrationIndexProjector.cs:65` |
| **Marked in spec** | `aggregates/Registration/registration.write-model.md:484` |

#### D-4 · Three response records are declared and never sent · Low

`SubmitRegistrationResponse`, `ResubmitRegistrationResponse` and `CancelRegistrationResponse` are the
declared `TResponse` of their endpoints, but all three handlers call `SendNoContentAsync`. The types are
unreachable, and the endpoint signature advertises a body that never ships.

| | |
|---|---|
| **Fix** | Delete the three records; change the endpoints to `RegistrationEndpointWithoutRequest` with no response type, or the platform's equivalent |
| **Code** | `modules/Registration/Registrations.WriteModel.Endpoints/V1/Registrations/{SubmitRegistration,ResubmitRegistration,CancelRegistration}/` |
| **Marked in spec** | Not marked, deliberately — the spec's HTTP contract (`204 No Content`) is already correct, and a reader of the spec is not affected. This is a code tidy-up |

#### D-5 · `RequestAmendmentCommand.AmendmentId` is commented "Caller-generated" · Low

It is server-generated at the endpoint (`AmendmentId.New()` in `RequestAmendmentEndpoint`), which is what
the API contract requires. The comment is a leftover from before that decision and is the kind of thing
the next reader trusts over the code beside it.

| | |
|---|---|
| **Fix** | One-line comment change: `// Server-generated at the endpoint` |
| **Code** | `modules/Registration/Registrations.WriteModel/Commands/RequestAmendment/RequestAmendmentCommand.cs:10` |
| **Marked in spec** | Not marked — the spec states server-generated in three places; the defect is a stale code comment only |

#### D-6 · The `ApproveAmmendment` namespace is misspelled · Low

Two `m`s, in both the folder and the namespace: `Magiq.Media.Registrations.Commands.ApproveAmmendment`.
The command type itself is spelled correctly.

| | |
|---|---|
| **Fix** | Rename the folder and namespace. It is a **public** namespace, so it is source-breaking for anything that names the type — in practice only this repo's own hosts and tests |
| **Do it with** | Any other Registration change that already touches the write model, rather than as a PR of its own |
| **Code** | `modules/Registration/Registrations.WriteModel/Commands/ApproveAmmendment/` |
| **Marked in spec** | `aggregates/Registration/registration.write-model.md:336` |

---

## 2. Open decisions

Spec and code disagree, or the code is unowned, and picking a side needs a call rather than a fix.

#### U-1 · Every summary row in a tenant lives in one DynamoDB partition · Medium

`RegistrationSummarySchema` passes no group key, so the emitted PK is `TENANT#{tenantId}#REGISTRATIONS`
with sort key `SUMMARY#{registrationId}` — one partition per tenant, holding every registration that
tenant will ever create. Neither GSI relieves it; both are alternative views of the same rows.

This looks deliberate — it is what makes a tenant-wide list a single query with no sort-key condition —
but it is undocumented and unbounded, and it contradicts the repo `CLAUDE.md` convention line
`TENANT#{TenantId}#{EntityId}`. The retention policy makes it worse than most: confirmed filings are
meant to be kept ten years and nothing removes them.

| | |
|---|---|
| **The call** | Accept it as a stated assumption with a scale bound (the RecordType registry took this route explicitly), or re-key the summary row and backfill |
| **Needs first** | An actual number. Registrations per tenant per year, at the largest customer. Nobody has one |
| **Related** | Possibly in scope for `projection-tables` (MM-003) — check before opening anything new |
| **Marked in spec** | `aggregates/Registration/registration.read-model.md:63` |

#### U-2 · The reference model registers `schemaVersion: null` · Low

`AddProjectionSchema<MediaItemReference>("media-registration-item-ref", "MEDIA_ITEM", schemaVersion: null)`
— every read model in the module declares `1`. The physical table name is `{tableName}-v{schemaVersion}`,
so the emitted name differs depending on how the platform treats null.

| | |
|---|---|
| **The call** | Confirm the emitted physical name against the CDK projection-table manifest, then either normalise to `1` or record why a reference model is versionless |
| **Risk if ignored** | A CDK table definition and a runtime lookup that disagree about a table name fail at runtime, not at deploy |
| **Marked in spec** | `aggregates/Registration/registration.write-model.md:489` |

#### U-3 · `RegistrationAuthority` normalisation is unverified and untested · Medium

`InitiateRegistrationHandler` applies `CultureInfo.InvariantCulture.TextInfo.ToTitleCase` after trimming.
`ToTitleCase` leaves a fully-uppercase word unchanged, so `"US Copyright Office"` is **expected** to
survive intact rather than becoming `"Us Copyright Office"`. The old spec asserted both readings in
different files.

No test pins it, and the normalised value is what gets stored **and indexed** — a search on the authority
matches the normalised form.

| | |
|---|---|
| **The call** | Write the test first, then decide. If title-casing acronyms is wrong for real authority names — and "US Copyright Office", "IP Australia", "BFI" suggest it is — the transform may be wrong altogether and a trim is enough |
| **Bigger question** | A controlled vocabulary is not implemented and the spec records that. Free-text plus a lossy transform is the worst of both: two officers can file with the same authority under two stored strings |
| **Marked in spec** | `aggregates/Registration/registration.write-model.md:385` |

#### U-4 · Three of the six published integration events have no consumer · Medium

`EventConsumers` subscribes to initiated, rejected and cancelled. Nothing subscribes to
`RegistrationSubmittedIntegrationEvent`, `RegistrationResubmittedIntegrationEvent` or
`RegistrationConfirmedIntegrationEvent`.

The old spec asserted a saga orchestrator consumed the submitted/resubmitted pair to trigger and retry
external dispatch. No such saga exists.

| | |
|---|---|
| **The call, three parts** | (a) Is the submitted/resubmitted pair meant to trigger the adapter's dispatch, and is that adapter in-repo, out-of-repo, or unbuilt? (b) Does a Compliance consumer for `media.registration.confirmed` exist outside this repo? (c) If any is genuinely unbuilt, does it move to a "specified but not built" register with an owner, or does the event stop being published? |
| **Why it matters** | An event nobody consumes is indistinguishable from a broken subscription. Today there is no way to tell whether the adapter integration is missing or simply lives elsewhere |
| **Marked in spec** | `context-overview.md:109` |

#### U-5 · No CLI rebuild verb exists for `Registration` · Medium

A corrupted, missing or back-filled projection cannot be rebuilt. Combined with unmeasured projection lag
and no staleness alarm, a failing projector is invisible until someone reports a stale read — and then
there is no remedy short of a manual replay.

| | |
|---|---|
| **The call** | Whether this is a Registration gap or a platform one. `TableRotationRegistry` already knows `media-registrations`, so the plumbing may be closer than it looks |
| **Related** | `projection-rebuild` (MM-032) is **Parked**. This may be the finding that unparks it, or it may simply be another row on it |
| **Marked in spec** | `aggregates/Registration/registration.read-model.md:325` |

---

## 3. Already owned elsewhere

Recorded so they are not re-raised as Registration findings.

| Item | Owner | Marked in spec |
|---|---|---|
| **`actor_type = "System"` is not enforced on the five `[System]` endpoints.** All five are HTTP-reachable by any tenant member, including `POST /confirm`, which finalises a filing as a permanent legal record. `authorization-matrix.md` calls this group "the most severe" on the platform | Authorization workstream — **MM-028 / MM-029**, blocked on `magiq-auth` issuing an `actor_type` claim | `aggregates/Registration/registration.api.md:93` |
| **`errorCode` does not reach the wire on any read endpoint.** Only the `Api` host installs `ErrorCodeResponseConfigurator`; `QueryApi` does not. Platform-wide, not Registration-specific | Platform SDK error model — **MM-039** | `aggregates/Registration/registration.api.md:426` |

---

## Incidental

`tests/integration/modules/Registration/Registration.IntegrationTests/AhocTest.cs` is entirely commented
out and contains a **real bearer JWT for `chase.ramone@magiqsoftware.com`**, committed to the repo.
Expired 2026-06-04, so not live. The file has no other content.

**Delete it.** Rotating is unnecessary given the expiry; leaving a token in git history because it
expired is a habit worth not forming.

---

## Suggested sequencing

1. **D-1 and D-2 together.** Both are about what a registration means to the rest of the platform, and
   both need a decision before a fix. They are one review — call it `registration-lifecycle` — not two.
2. **U-3 next**, because it is one test and the answer may retire the transform entirely.
3. **D-4, D-5, D-6** ride along with whatever touches the module next. None justifies a PR.
4. **U-1, U-2, U-5** are scale and operability, and each has an existing workstream that may already own
   it — check `projection-tables` (MM-003) and `projection-rebuild` (MM-032) before opening anything.
5. **U-4 is a question for Tom or whoever owns the adapter**, not an engineering task yet.
