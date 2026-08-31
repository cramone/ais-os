---
id: MM-031
type: review
project: magiq-media
workstream: pending-decisions
raised-by: []
status: done
outcome: decision-only
todo-id: f9600ca6-4b0e-5bbf-bb1d-553d94c41dea
created: 2026-08-25
---

> **Backfilled into the review cycle 2026-08-31 as MM-031.** No plan and no research left — the evidence is complete and the code understood. **Two decisions are outstanding and neither is logged in decisions/log.md** (checked 2026-08-31): X-11.21 idempotency, adopt or retire — the middleware is deployed and nothing sends the header, and the header name mismatch means clients following the contract got zero protection silently; and BI-1 — build, delete the spec, or badge it design-only with a deadline. Log both via /decision when made.

# Two decisions blocking code work

_Opened 2026-08-25. **Parked deliberately** — both surfaced during the spec-drift review. Neither is a
research question: the evidence is complete and the code is understood. **What is missing is a call.**_

---

## Why these two are together

They have nothing in common as subjects. They are here because they share a shape: **each blocks work that
is otherwise ready to start**, and each has been sitting in an ambiguous state long enough that the
ambiguity is itself doing damage.

The idempotency one is worse than it looks — the current state is not "undecided", it is **"the docs and
the code contradict each other about whether a feature exists"**, and clients are following the docs.

---

# Decision 1 — Idempotency: adopt or retire?

**Finding:** X-11.21 (🟠 blocker) · **Related:** X-10.5

## What is actually true

**The mechanism is real, deployed, and functional.**

| | |
|---|---|
| Package | `Magiq.AspNetCore.Idempotency`, referenced by `src/hosts/Api/Api.csproj` |
| Wiring | **Global middleware**, auto-discovered as an `ITenantStartup` at `ConfigureOrder = Authentication + 60`. Not opt-in, not per-endpoint |
| Coverage | **Every write endpoint on the `Api` host.** `QueryApi` does not reference the package |
| Table | `media-idempotency-keys` — **provisioned by the CDK**, PK `TENANT#{t}#OWNER#{o}#{key}`, TTL attribute `Ttl` |
| Window | **24 hours, and not configurable** — `IdempotencyOptions` binds no configuration section |

**And nothing uses it.** No client code, no integration test, no Postman collection in the repo sends the
header. The only references outside the wiring are **three code comments asserting the feature does not
exist** — in `BulkInitiateAssetUploadCommand`, `CreateCollectionRequest` and `ArchiveAssetEndpoint`.

> ### The bug that makes this urgent rather than merely untidy
>
> **The header is `Idempotency-Key`. Every document said `IdempotencyKey`.**
>
> A client following the published contract sends the unhyphenated form, the middleware does not recognise
> it, and the request **executes with no replay protection at all** — silently, with a 2xx. There is no
> warning and no way for the caller to tell. The spec is corrected; **the code comment in
> `RequestAmendmentRequest.cs:17` is not.**

## What it does, precisely — because the name oversells it

```csharp
if (await store.ExistsAsync(tenantId, ownerId, key, ct))
{
    context.Response.StatusCode = StatusCodes.Status409Conflict;
    return;                              // no body
}
await store.MarkAsync(tenantId, ownerId, key, DateTimeOffset.UtcNow.Add(opts.Window), ct);
await next(context);                     // ← marked BEFORE execution
```

Four properties, none of them obvious from the word "idempotency":

1. **It is replay *rejection*, not idempotent replay.** A repeat key gets a bare `409` — **not the original
   response.** A client that lost its response to a timeout still cannot learn whether the operation
   succeeded; it has to query.
2. **The key is burnt before execution.** A request that then 500s or is killed has already consumed its
   key, so an honest retry gets `409` for the rest of the 24-hour window even though nothing was created.
3. **It fails open three ways, all silent** — unauthenticated, no header, or a principal missing the tenant
   or owner claim.
4. **The `409` has no `ProblemDetails` body.** It is the only response in the API that bypasses the error
   contract entirely.

## What retry-safety actually rests on today

**Client-supplied aggregate ids**, on three endpoints: `POST /v1/assets/uploads/bulk` (required),
`POST /v1/collections` and `POST /v1/collections/bulk` (optional). Re-submitting reuses the ids and the
event store's `attribute_not_exists(AggregateVersion)` rejects the duplicates. The comment on
`BulkInitiateAssetUploadCommand` explains why it matters — *"this endpoint can create up to a hundred at a
time"*.

**It protects creation only.** Retrying `approve`, `publish`, `confirm` or `move` has no protection of any
kind.

## The options

| | What it means | Cost |
|---|---|---|
| **A. Adopt** | Fix the header name in the remaining code comment, declare the header in OpenAPI (**X-10.5**), have clients send it. Optionally also fix mark-before-execute so a failed request does not burn its key | Small. The infrastructure is already deployed and paid for |
| **B. Adopt and upgrade** | As A, plus store the response and replay it — turning rejection into true idempotency | Larger; a platform-SDK change, not an app change |
| **C. Retire** | Drop the package reference and the CDK table. Rely on client-supplied ids, and extend those to the endpoints that need them | Small, and honest. Loses protection for state transitions |

**Recommendation: A.** The feature is built, deployed and free; the only thing wrong is that nobody knows
it exists and the documented header name was wrong. B is the right end state but is a separate piece of
work in another repo. C throws away something already paid for.

**What must not persist is the current state** — a deployed feature that the code comments deny, with a
published header name that does not work.

### Decide these together

- Does **mark-before-execute** get fixed, or is burning a key on a failed request acceptable?
- Does `QueryApi` need it? *(Probably not — reads are not the risk.)*
- Should the 24-hour window become configurable? It cannot be today.

---

# Decision 2 — BI-1: what happens to the bulk-import spec?

**Finding:** BI-1 · **Owns 16 of the 16 remaining CI warnings**

## What is actually true

`docs/spec/contexts/Catalog/aggregates/` carries two fully specified aggregates —
**`BulkFolderImportJob`** and **`BulkMediaImportJob`** — with write models, read models, API contracts and
scenarios. Verified 2026-08-25:

| | State |
|---|---|
| Aggregate classes | **None** |
| Commands, handlers, projectors | **None** |
| Queues | Named **only in a CDK comment** — *"add with bulk import implementation"* |
| Tables | **Zero** `bulk` entries in `projection-tables.manifest.json`, which is authoritative |
| S3 bucket | `media-bulk-import-inputs` does not exist |
| Routes | No `/import` route; no `/v1/import-jobs/...` route |

The **inline** bulk endpoints — `/bulk`, `/bulk-paths`, `POST /v1/items/bulk` — are real and shipped. Only
the **async job** feature is absent.

W27 already merged the one piece of unique content (the SQS/DLQ queue configuration) into
`shared/bulk-operations.md` and put a hard *"none of this is built"* badge on that section.

## Why it is the last thing between CI and green

`check-spec-sections.py` reports **`fail 0 · warn 16 · rename backlog 0`**, and **all 16 warnings are
these two aggregates** — missing `Authorization`, `Projection Handlers`, `Read Model Types`, `Consistency`
and so on. Every other owning unit is at zero.

Those sections cannot honestly be written, because there is nothing to describe. **The warnings are correct
and will not go away by writing more spec.**

## The options

| | What it means | Consequence |
|---|---|---|
| **A. Build it** | The feature ships; the spec becomes true | Real project. Nothing else on the board depends on it |
| **B. Delete the spec** | Remove both aggregate folders; keep the async pattern in `bulk-operations.md` as design | CI green. Loses the detailed design — recoverable from git, and it was never validated against code |
| **C. Badge and exempt** | Keep the spec, mark both aggregates *design-only*, add a `BI-1` exemption to the section checker | CI green. Keeps the design visible. **Adds an exemption to a guard whose whole value is being unconditional** |

**Recommendation: C, with a deadline — or B if there is no date.** The design is worth keeping if the
feature is genuinely coming; it is a liability if it is not, because a fully specified aggregate with no
code is exactly what this whole review has been cleaning up. **The question to answer is not "is the design
good" but "is this being built, and roughly when".**

> ⚠ **The precedent matters more than the warnings.** W18 retired the `⚠ TRUNCATED` exemption specifically
> because *"a marker only helps for damage somebody already noticed"*, and made the truncation guard
> unconditional. Adding an exemption to the sibling guard is a step back in the other direction. If C is
> chosen, the exemption should carry the deadline in its comment and fail again when it passes.

---

## What unblocks when these are decided

| Decision | Unblocks |
|---|---|
| Idempotency | X-11.21 leaves the 🟠 gate. X-10.5 (declare headers in OpenAPI) becomes actionable |
| BI-1 | `check-spec-sections.py` goes green; the W2 exit criterion on the spec board finally closes |

Neither blocks the two 🔴 security items — **those are independent and should start regardless.**

---

## Related

- `plans/prod-readiness/prod-readiness-gate.md` — where both appear under *Decisions still owed*
- `plans/spec-drift-review/spec-repo-drift-review.md` — X-11.21, X-10.5, BI-1 in full
- `docs/spec/shared/api-conventions.md § Idempotency` (magiq-media repo) — the corrected behaviour
- `docs/spec/shared/bulk-operations.md § Async Bulk Import Jobs` — the badged design
