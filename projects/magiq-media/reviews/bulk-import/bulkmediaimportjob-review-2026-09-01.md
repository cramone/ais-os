---
id: MM-037
type: review
project: magiq-media
workstream: bulk-import
raised-by: [MM-022]
status: draft
outcome: pending
todo-id: -
created: 2026-09-01
---

> **Split out of `plans/spec-drift-review/spec-repo-drift-review.md` § C.6 on 2026-09-01**, where
> `BulkFolderImportJob` and `BulkMediaImportJob` were tracked as one three-row block (BI-1/2/3). This
> review covers **BulkMediaImportJob only**; its sibling is
> [`bulkfolderimportjob-review-2026-09-01.md`](./bulkfolderimportjob-review-2026-09-01.md) (MM-036).

# BulkMediaImportJob — a published aggregate with no code, and a multi-phase design with a hole in it

_Scope: **BI-1, BI-2, BI-3** as they apply to `BulkMediaImportJob`. Four spec files, 818 lines, six
published routes, zero implementation._

_Every claim verified against `src/`, `docs/spec/` and the CDK on 2026-09-01._

---

## The verdict, up front

**Nothing exists at any layer** — same as its sibling, same grep, same zero. But **this aggregate is not
the same size of decision**, and that is the reason the two were worth separating.

The folder importer is one phase: read paths, create folders, report. The media importer is **three phases
with a client round-trip in the middle** — the worker issues pre-signed upload URLs, the client uploads
assets out-of-band, then calls back to confirm. That shape carries a specific, named, unanswered question:

> **BMI-2 — "uploads never arrive": no timeout specified.**

A job that waits on a third party with no timeout is not an implementation detail left for later. It is
the part of the design that decides whether the aggregate is finishable, and it is blank. **Anyone
estimating this from the spec's completeness would estimate it wrong.**

---

## Findings

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | **BMI-A** *(was BI-1, media half)* | **High** | A full aggregate — write-model (with status transitions), read-model and API spec across **six routes** | **Nothing exists at any layer.** No aggregate, commands, events, endpoints, read models, projectors or worker | 4 spec files under `contexts/Catalog/aggregates/BulkMediaImportJob/` |
| ☐ | **BMI-B** *(was BI-2, media half)* | **High** | `media-bulk-media-imports` SQS queue; shared `media-bulk-import-job-items` table; `media-bulk-import-inputs` S3 bucket | **None provisioned.** CDK comment placeholder only; the bucket appears nowhere; zero `bulk` entries in the projection-table manifest | `cdk .../sqs-queues.ts` (comment only) |
| ☑ | **BMI-C** *(was BI-3, media half)* | ~~Med~~ **closed 2026-08-31, travelled closed** | `api-conventions.md § Pagination` documents import-job pageSize caps (50/200) | **Closed:** BI-3 banner added there 2026-08-31; the table was deliberately kept rather than deleted, so as not to pre-empt this decision. Listed so the caps are not re-litigated | `api-conventions.md § Pagination` |
| ☐ | **BMI-D** | Med | — | **Eight of the tree's sixteen remaining CI warnings are this aggregate's**, including `write-model.md: missing 'Consumed Integration Events'` — which is not a prose gap but a real unanswered question: *which* asset events does the job consume to know an upload landed? | `.github/scripts/check-spec-sections.py` |
| ☐ | **BMI-E** | **High** | The upload phase completes when the client calls `POST /v1/import-jobs/{jobId}/confirm-uploads` | **No timeout, no expiry, no abandonment path is specified anywhere** for a job parked in the upload phase. The spec's own scenario index flags this (BMI-2) and does not answer it | `bulkmediaimportjob.scenarios.md § Index` |

### The six published routes

```
POST   /v1/collections/{collectionId}/media-items/import
GET    /v1/import-jobs/{jobId}/upload-urls
POST   /v1/import-jobs/{jobId}/confirm-uploads
GET    /v1/import-jobs/{jobId}
GET    /v1/import-jobs/{jobId}/items
DELETE /v1/import-jobs/{jobId}
```

**Three are shared with the folder importer** (`GET {jobId}`, `GET {jobId}/items`, `DELETE {jobId}`);
three are this aggregate's own, and all three of those belong to the upload round-trip. **The shared
`/v1/import-jobs/**` surface binds both aggregates** — decide it once, in the workstream, not twice.

---

## Why the upload phase is the whole review

The other findings are the same shape as the folder importer's and can be read there. This one is not.

**The design asks the platform to hold a job open across a client-controlled interval with no stated
bound.** Three things follow, none of them written down:

1. **Nothing reclaims the job.** No timeout scanner, no expiry, no abandonment. `TimeoutScanner`
   hard-codes `SagaType = "ASSET_INGESTION"` (established by W21 while specifying the signing saga), so a
   bulk-import scanner is **new code, not configuration** — the same finding that surprised the
   DocumentSigning review.
2. **Nothing bounds the pre-signed URLs.** X-11.25 found the existing upload path has a **15-minute TTL as
   a compiled constant** with one shared `expiresAt` across all multipart parts. A bulk import issuing
   URLs for 500 assets inherits that: the client cannot finish a large import inside one TTL, and the spec
   does not say what happens when URLs expire mid-import.
3. **The redelivery interaction is already known to be wrong.** W27 established batch-size-1 with a
   30-minute visibility timeout means **a redelivery restarts the whole job**. Combined with (1), a job
   that stalls in the upload phase can be redelivered, restart, and re-issue URLs — with no dedup rule
   specified (BMI-3, also flagged and unanswered).

> **These compound.** Individually each is a gap; together they describe a job that can be started twice,
> never finished, and never cleaned up. **That is not a documentation finding — it is the reason this
> aggregate should not be built from the spec as written**, whatever is decided about whether it is built
> at all.

---

## What the decision looks like

The same three options as the folder importer — build, park honestly, delete — with one difference that
should be stated plainly:

**Build is materially more expensive here, and the spec understates it.** The folder importer could be
estimated from its spec. This one cannot: BMI-2 (timeout), BMI-3 (dedup) and the `Consumed Integration
Events` gap are each a design decision, and two of them interact with defects already open against the
existing upload path (X-11.25, X-11.26). **A build estimate taken from the route count would be wrong by
more than a factor.**

**Park and delete cost the same here as for the sibling** — hours either way, plus the banner work below.

---

## Banner state, checked 2026-09-01

Same as the sibling, and the drift review's note was stale in the same way:

- **`scenarios.md` carries a `⚠ INTENT, NOT BEHAVIOUR — none of this exists` block** at line 6 (W26),
  naming `BulkMediaImportWorker` and its queues. The drift review said it carried none.
- **`api.md`, `read-model.md` and `write-model.md` carry nothing.** The API file publishes six routes,
  request/response bodies and a traceability table with no indication that none of it is served.
- `bulk-operations.md § Async Bulk Import Jobs` **is** banner-ed (W27, `⛔ None of this section is built`,
  verified four ways). **Copy that wording rather than inventing a second form.**

---

## Related

- [`bulkfolderimportjob-review-2026-09-01.md`](./bulkfolderimportjob-review-2026-09-01.md) — MM-036, the
  sibling; simpler, and separable from this one on everything except the shared `/v1/import-jobs/**` surface
- `plans/spec-drift-review/spec-repo-drift-review.md` — where BI-1/2/3 lived until 2026-09-01; **X-11.25**,
  **X-11.26** and **X-11.20** are the existing upload-path rows this design would inherit
- `docs/spec/shared/bulk-operations.md` § Async Bulk Import Jobs — the ⛔ banner, and the queue
  configuration (900 s / 1800 s visibility, `maxReceiveCount: 3`, batch size 1) W27 salvaged
- `plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` — W26 and W27, the two units that
  touched this tree
