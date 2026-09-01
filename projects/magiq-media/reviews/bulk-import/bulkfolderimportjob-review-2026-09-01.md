---
id: MM-036
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
> `BulkFolderImportJob` and `BulkMediaImportJob` were tracked as one three-row block (BI-1/2/3). They are
> two aggregates with different shapes and different reasons to exist, and the shared block made them look
> like one decision. This review covers **BulkFolderImportJob only**; its sibling is
> [`bulkmediaimportjob-review-2026-09-01.md`](./bulkmediaimportjob-review-2026-09-01.md) (MM-037).

# BulkFolderImportJob — a published aggregate with no code at any layer

_Scope: **BI-1, BI-2, BI-3** as they apply to `BulkFolderImportJob`. Four spec files, 639 lines, five
published routes, zero implementation._

_Every claim here was verified against `src/`, `docs/spec/` and the CDK on 2026-09-01, not taken from the
drift review's summary — two of that summary's statements turned out to be stale and are corrected below._

---

## The verdict, up front

**Nothing exists at any layer.** A repo-wide grep across `src/**/*.cs` for `BulkFolderImportJob`,
`BulkFolderImportWorker`, `ImportJob` and `import-jobs` returns **zero hits** — no aggregate, no commands,
no events, no endpoints, no read models, no projectors, no worker. Meanwhile `docs/spec/` publishes four
files describing the feature in the present tense, and **three of those four carry no unbuilt-feature
banner at all.**

**The decision is not "how do we document this" — it is "does this feature exist."** Everything else
follows. If the answer is yes-later, these files are a design record and need banners plus a home that
says *design*. If the answer is no, they are deleted and `bulk-operations.md § Async Bulk Import Jobs`
loses its folder half. **Both answers are cheap. Neither has been given, and the files have been readable
as shipped contract since 2026-07.**

> **Why this is worth splitting from its sibling.** The folder importer is the *simpler* of the two — one
> phase, no upload round-trip, no third-party wait — so it is the one that could plausibly be built in a
> sprint if the answer is yes. Bundling it with the media importer, which has an unspecified timeout on a
> phase that waits on the client, made the whole block look like a large piece of work. It is not one
> piece of work.

---

## Findings

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | **BFI-A** *(was BI-1, folder half)* | **High** | A full aggregate — write-model, read-model and API spec across **five routes** | **Nothing exists at any layer.** No aggregate, commands, events, endpoints, read models, projectors or worker | 4 spec files under `contexts/Catalog/aggregates/BulkFolderImportJob/` |
| ☐ | **BFI-B** *(was BI-2, folder half)* | **High** | `media-bulk-folder-imports` SQS queue; shared `media-bulk-import-job-items` table; `media-bulk-import-inputs` S3 bucket | **None provisioned.** The CDK carries a comment placeholder naming the queue as future work; the bucket appears nowhere; the shared table has **zero entries in the authoritative projection-table manifest** | `cdk .../sqs-queues.ts` (comment only) |
| ☑ | **BFI-C** *(was BI-3, folder half)* | ~~Med~~ **closed 2026-08-31, travelled closed** | `api-conventions.md § Pagination` documents import-job pageSize caps (100/500) | **Closed:** that section now carries a BI-3 banner stating that none of the three `/v1/import-jobs/**` routes exists and that the block resolves with BI-1. The table was deliberately **kept rather than deleted** — deleting it would pre-empt the decision this review exists to frame. Listed here so the caps are not re-litigated | `api-conventions.md § Pagination` |
| ☐ | **BFI-D** | Med | — | **Eight of the tree's sixteen remaining CI warnings are this aggregate's** — `check-spec-sections.py` reports them under owning unit BI-1, and they cannot be closed by writing prose because the sections describe code that does not exist | `.github/scripts/check-spec-sections.py` |

### The five published routes

```
POST   /v1/collections/{collectionId}/folders/import
GET    /v1/import-jobs/{jobId}
GET    /v1/import-jobs/{jobId}/items
GET    /v1/import-jobs
DELETE /v1/import-jobs/{jobId}
```

**Four of the five are shared with the media importer** — only the `POST` differs. That is the strongest
argument for one workstream and two reviews rather than two workstreams: whatever is decided about
`/v1/import-jobs/**` binds both aggregates, while the two `POST` routes are independent.

---

## Two corrections to the drift review's account

**(a) The banner claim was stale and understated.** The drift review's remaining-work list said
*"`bulkfolderimportjob.api.md` and `.scenarios.md` carry no unbuilt-feature banner."* Checked
2026-09-01: **`scenarios.md` does carry one** — a `⚠ INTENT, NOT BEHAVIOUR — none of this exists` block at
line 6, naming `BulkFolderImportWorker` and its queues, added by W26. The real gap is wider than the row
said: **`api.md`, `read-model.md` and `write-model.md` carry nothing**, and the API file is the one a
consumer team would read first.

**(b) `bulk-operations.md` is already banner-ed, and its async section is not the problem.** W27 added a
hard `⛔ None of this section is built` block at `§ Async Bulk Import Jobs`, verified four ways (no worker
in `src/hosts/`, queues named only in a CDK comment, zero `bulk` entries in the projection-table manifest,
no `media-bulk-import-inputs` bucket). **That file is honest; the four aggregate files are not.** Any
remediation should copy that banner's wording rather than invent a second one.

---

## What the decision looks like

Three options, and the review's job is to make them comparable rather than to choose:

| | Build it | Park it honestly | Delete it |
|---|---|---|---|
| **Spec files** | Stay; become the implementation target | Stay; gain the `bulk-operations.md` banner on all four, and move under a `design/` marker | Deleted; `api-conventions.md`'s pagination rows and `bulk-operations.md`'s folder half go with them |
| **CI warnings** | Close naturally as sections gain real content | **Stay at 8** — or the guard gains a documented exemption for design-status files, which is a change to the guard's contract | Close immediately; tree reaches `warn 0` |
| **Cost** | Real: aggregate, 5 endpoints, worker, queue, projector, the shared items table | Hours | Hours |
| **Risk** | None new | The files keep being found by people who assume spec means shipped | Losing a design that was thought through once and would be re-derived worse |

> **The `warn 0` framing is a trap worth naming.** The drift review listed BI-1 as *"the only thing
> standing between CI and `warn 0`."* True, and it is not a reason to delete the files — a guard warning
> is the symptom, and deleting the spec to silence it would be optimising for a green board over a real
> answer. Whichever way the decision goes, it should go on the feature's merits.

---

## What is genuinely unanswered in the design

Worth knowing before anyone calls this "spec'd and ready to build" — from `bulkfolderimportjob.scenarios.md`,
whose own index flags them:

- **BFI-2 — a chunk fails partway through: no compensation specified.** The job's failure semantics are
  undefined, and folder creation is not idempotent by construction.
- **BFI-3 — the same import submitted twice: no dedup rule specified.** Related, and worse than it looks:
  W27 established that batch-size-1 with a 30-minute visibility timeout means **a redelivery restarts the
  whole job**, so chunk idempotency cannot be deferred to a later phase the way the retired changelog
  scheduled it.
- **The archive cascade interaction is unconsidered.** X-11.41 found `FolderMediaItemsIndex` is add-only;
  a bulk folder import that lands under a folder later archived inherits that defect at import scale.

**These are design gaps, not documentation gaps** — they cannot be closed by writing, only by deciding.

---

## Related

- [`bulkmediaimportjob-review-2026-09-01.md`](./bulkmediaimportjob-review-2026-09-01.md) — MM-037, the
  sibling aggregate; the two share four routes, one items table and one input bucket
- `plans/spec-drift-review/spec-repo-drift-review.md` — where BI-1/2/3 lived until 2026-09-01
- `docs/spec/shared/bulk-operations.md` § Async Bulk Import Jobs — the ⛔ banner to copy, and the queue
  configuration W27 salvaged from the retired `BULK-IMPORT-SPEC-UPDATES.md`
- `plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` — W26 wrote the scenarios file; W27
  retired the changelog and added the `bulk-operations.md` banner
