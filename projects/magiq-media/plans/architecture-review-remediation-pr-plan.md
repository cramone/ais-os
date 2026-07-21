# Architecture-Review Remediation — PR Breakdown & Delivery Plan

_magiq-media · How to break the 11 architecture reviews in `D:\source\github\magiq-media\docs\reviews\` (ex-`archived\`) into ordered, dependency-aware, PR-sized work._
_Author: architecture pass (AI-assisted), for Chase Ramone · Drafted 2026-07-19 · Revised 2026-07-20._
_Status: **DRAFT for review** — nothing implemented from this doc yet. Scope confirmed with Chase: **everything, phased** (all findings, pre-prod blockers first). ADO items **drafted here, not created**._
_**2026-07-20 revision:** all work owners set to **Chase** (single-owner pass — re-delegate later as needed). **Authorization (Stream C / Phase 3) and the transactional-outbox PR (B4), plus the INV-2 outbox spike, are deferred and split into a companion plan: `architecture-review-authz-and-outbox-deferred-plan.md`.** Their production-gate obligations remain (see §16); only the sequencing is moved out of this doc._

> **Companion to** the reviews in `docs/reviews/`. This plan does not re-argue any finding — it consumes them and answers one question: _in what order, grouped into which PRs, does this get fixed without the seams staying half-broken between merges._ Every PR cites the finding IDs it closes so you can trace back to the reasoning.

---

## 1. Executive summary

The reviews describe **one system with a severed spine and a lot of independent limb injuries.** Those are two different planning problems and want two different slicing strategies:

1. **The spine — the asynchronous choreography — does not run at all.** Every worker/consumer/saga host is missing the platform `IMessageBus`, so the first integration event any of them tries to publish throws; three Processing events have no publisher registered anywhere; and the SNS filter policies drop or misroute several events the code consumes. This is a **strict dependency chain** (`XM-C1 → C2 → C4 → C3/C5/C6`, cross-checked as `S-08 → S-09 → S-12/S-13 → S-01..S-06` in the independent sweep). Nothing downstream of the API host — the whole upload→scan→validate→process→complete pipeline and the `AssetIngestionSaga` — works until this chain lands, **in order**, and is verified in a live SNS environment. This is Phase 1 and it blocks the value of almost everything else.

2. **The limbs — per-module correctness, security, and contract defects — are mostly independent vertical slices.** Authorization is absent in *every* module (8 Criticals of the same shape); a cluster of projector copy-paste bugs silently corrupt read models; consumers swallow command results; reference projectors aren't reorder-safe. These don't have to wait for the spine, and several are trivial-but-critical (a one-line `Status="Succeeded"` on a *failed* job; an inverted eligibility guard that forges authority references). They parallelize across the team once a few shared foundations exist.

The plan therefore uses **two slicing rules at once**:

- **Cross-cutting concerns get a shared foundation PR + thin per-module enforcement PRs** (authorization, consumer result-handling, tenant-from-attribute, reference-projector watermarks). Fixing authorization eight times from scratch is eight chances to do it differently; fixing it once in the platform and enforcing it eight times is reviewable and consistent.
- **Module-specific bugs get vertical slices** — one PR per coherent defect cluster inside a module, independently buildable and reviewable, following the repo's existing GitFlow / one-PR-per-concern convention.

**Three work packages are already planned and in flight — do not re-plan them here**, just sequence around them: `s13-uniqueness-atomicity-remediation-plan.md` (name-reservation/counter atomicity + folder-archive cascade → resumable saga; covers `COL-H6 / FOL-H5 / MI-H4 / MP-H5 / RT-H3` and the cascade partial-failure half of `FOL-C3`), `api-consistency-remediation-plan.md` (status codes, URL naming, request/response hygiene, versioning gate — Stages 0–5 substantially done), and `content-category-remediation-plan.md` (MediaCategory + MIME classification — substantially done). Where a finding below is owned by one of those, it is marked **[in-flight: …]** and excluded from a new PR.

**The single hard rule:** do not re-enable prod/staging deploys until Phase 1 (backbone) is landed *and* verified end-to-end in a live SNS environment. Everything else can be reordered around team capacity; the backbone cannot.

---

## 2. Source reviews & finding inventory

Eleven reviews (excluding `archived\`), all dated 2026-07-19 except where noted, all returning the same verdict: **NOT production-ready.**

| Review | Aggregate/scope | Headline count | Critical themes |
|---|---|---|---|
| `cross-module-integration-review.md` | Whole BC — seams | 7 Critical, 9 High, 8 Med, 4 Low (`XM-*`) | Backbone dead in prod; filter⇄bridge drift; silent-drop/DLQ consumers |
| `cross-module-impact-sweep-2026-07-19.md` | Whole BC — independent 2nd opinion (`S-*`) | 4 Critical, 13 High, 7 Med, 2 Low | Converges with the above; adds `S-17` (RecordType projector not in-host), `S-10` (wrong-host publisher) |
| `assetmanagement-architecture-review.md` | Asset | 3 Critical + High cluster | Authz absent; S3 delete-before-guard; infection projection gap |
| `processing-processingjob-architecture-review.md` | ProcessingJob | 1 Critical + High cluster | Failed→Succeeded projector; no completion driver; swallowed failures |
| `catalog-collection-architecture-review.md` | Collection | 2 Critical + High cluster | Authz absent; archive hard-mutates descendants |
| `catalog-folder-architecture-review.md` | Folder | 3 Critical + High cluster | Authz + owner-from-caller; move has no cycle guard; archive cascade |
| `catalog-mediaitem-architecture-review.md` | MediaItem | 2 Critical + High cluster | Authz; GDPR purge unguarded; active-items counter never maintained |
| `catalog-mediaprofile-architecture-review.md` | MediaProfile | 1 Critical + 6 High | Authz; compiled-template data loss; conformance model self-contradicts ADR-010 |
| `metadata-recordtype-architecture-review.md` | RecordType | 4 Critical + High cluster | Authz; projector data-corruption trio; last-field-removal bricks aggregate |
| `changerequests-architecture-review.md` | MediaChangeRequest | High cluster (CR-B1 Critical-in-effect) | Spec 3-way inconsistent; snapshot drops participants; read authz |
| `registration-registration-architecture-review.md` | Registration | 2 Critical + High cluster | Authz + System-actor forgery; inverted eligibility guard; dead search |

**Convergence note:** the two cross-module reviews were written independently and land on the same seam defects — treat that as corroboration, not double-counting. Where they disagree (`XM-H3/H4` "unconditional/last-write-wins" vs the sweep's "looks version-guarded" read of the same projectors), that contradiction is a **spike** in Phase 0, not an assumption baked into a PR.

---

## 3. Organising principles

**P1 — Pairing is mandatory where a seam has two ends.** An SNS filter allowlist lives in `cdk-magiq-media`; the consumer bridge lives in the app. Adding one without the other either drops the event (filter missing) or DLQs it forever (bridge missing). A GitHub PR can't span two repos, so each such pair is **one User Story with a Task (and PR) per repo**, both PRs citing the same `AB#<story-id>` and landing behind a shared merge gate so neither ships alone. Same rule for "publisher registration + the event that needs it."

**P2 — Shared foundation before per-module enforcement.** Authorization, consumer result-handling, tenant-sourcing, and reference-projector watermarks are one design applied N times. Each gets a foundation PR (platform/shared) that the per-module PRs depend on. This keeps the N applications identical and lets the foundation be reviewed once, hard.

**P3 — Vertical slice per defect cluster.** A module PR closes one coherent cluster (e.g. "MediaItem summary/version projector correctness"), not "all of MediaItem." Independently buildable, independently revertable, small enough to review in one sitting. Follows the in-flight plans' one-concern-per-PR convention.

**P4 — Trivial-but-critical jumps the queue.** `PJ-C1` (failed jobs read as "Succeeded"), the `RT-P1/P2/D1` corruption trio, and `RG-C2` (inverted guard that forges authority references) are days-of-effort-total but high-severity. They ride in early, small PRs rather than waiting behind the big refactors.

**P5 — Don't duplicate in-flight plans.** Reservation atomicity, API-consistency, and MediaCategory are already planned/landing. This plan sequences around them and flags overlaps; it does not restate their work.

**P6 — Docs/spec fixes co-locate with the code change that makes them true** (repo convention), except the pure spec-reconciliation batches (`Phase 5`), which gate the not-yet-built wiki auto-publish and are better as focused doc PRs.

**Branch/PR convention (from the repos' CLAUDE.md + the s13 runbook):** GitFlow, branches cut from `develop` as **`feature/chase/<ticket>-<slug>`** — the `<ticket>` is the ADO work-item ID and is **not optional**: it's the token that links the GitHub PR back to the Media board (via the Azure Boards GitHub app + an `AB#<ticket>` mention in the PR title/description). One independently-buildable PR per work item; build + test green after each; `Result<T,DomainError>` (no domain exceptions escape handlers), strongly-typed `Id<T>`, FastEndpoints, central `Directory.Packages.props`, abstractions-before-implementations. Three repos in play: **platform** (`aspnetcore-platform`), **app** (`magiq-media`), **cdk** (`cdk-magiq-media`) — all on **GitHub**, while work items live in **Azure DevOps**, so the `AB#` mention (not ADO's native Development panel, which only sees Azure Repos) is what ties code to board. **Confirm the Azure Boards GitHub integration is installed before relying on this.**

**Ownership (this revision):** every item below is owned by **Chase** for now — a deliberate single-owner pass so the plan reads as one accountable backlog rather than a pre-split assignment. `→ Chase` on each PR reflects that; re-delegate to Estelle Wu (API layer / authz enforcement / endpoint-validation-error-contract) and Akshay Gaikwad (UI-integrations / CDK filter-topology / search indexer) at scheduling time when capacity is being planned.

---

## 4. The dependency spine (the one ordering constraint)

```
                 ┌─────────────────────────────────────────────────────────┐
   PHASE 1       │  A1 publish-unblock  (S-08/09/10 = XM-C1/C2)  ★ROOT       │
   (backbone)    │        │                                                 │
                 │        ├─► A2 SNS test env (S-11)  ─┐                     │
                 │        ├─► A3 EventConsumers rewire (S-12/13 = XM-C4)     │
                 │        └─► A4 filter/bridge pairs (S-01..06 = XM-C3/5/6)  │
                 │                     │                                     │
                 │                     └─► A5 verify ingestion e2e (S-22)  ◄─┘
                 └─────────────────────────────────────────────────────────┘
                          │ (A1 landed)
        ┌─────────────────┴───────────────┐
        ▼                                  ▼
  PHASE 2 safety                     PHASE 4 module bugs
  B1 consumer/tenant                 (mostly independent;
  B2 saga concurrency                 a few need A1 or B*)
  B3 ref-projectors
        └──────────────► PHASE 5 hygiene ──► PHASE 6 deferred features

  PHASE 3 authz (C0 + C1..C8)  and  B4 outbox  → DEFERRED to
  `architecture-review-authz-and-outbox-deferred-plan.md`. Neither
  blocks anything remaining in this doc; both stay on the prod gate (§16).
```

Now only one node is a true blocker inside this doc: **A1** (everything async). `A2` must exist before `A5` can *verify* anything. (The authz foundation **C0**, previously the second blocker, only ever blocked C1–C8 — all moved to the companion plan.) Phases 2, 4, and 5 otherwise run concurrently subject to team size. Phase 6 is product-gated (Phase 0 `INV-4`).

**Deploy blocker to fix inside Phase 1, not later:** `XM-M7` — `bin/magiq-media.ts` defaults `ORGANIZATION_ID` to `o-abc123test`; if that reaches a real deploy the ECR org-condition denies every Lambda's image pull (cold-start 403) and *nothing* runs. Fold into `A2`.

---

## 5. Work streams (epics)

| Stream | Epic | Phase(s) | Nature |
|---|---|---|---|
| **A** | Async integration backbone | 1 | Strict chain; cross-repo pairs; verify in live SNS |
| **B** | Distributed-systems safety | 2 | Shared foundations: result-handling, tenant, saga OCC, ref-projectors _(outbox B4 → companion plan)_ |
| **C** | ~~Authorization~~ | ~~3~~ | **DEFERRED → `architecture-review-authz-and-outbox-deferred-plan.md`** (1 foundation + 8 per-module slices; still a prod gate) |
| **D** | Module correctness bugs | 4 | Vertical slices per module/cluster; parallelizable |
| **E** | Contract, validation & spec hygiene | 5 | Batched cleanups; references api-consistency plan |
| **F** | Deferred choreography features | 6 | Product-gated: review saga, DocumentSigning, reprocessing/checkout timeouts |
| **G** | Observability | 1–2 (threaded) | Correlation id, per-flow/saga metrics, drift alarms |
| **—** | _(in-flight)_ Reservation atomicity / API-consistency / MediaCategory | ongoing | Owned by existing plans; sequenced around |

---

## 6. Phase 0 — Spikes & decisions (cheap, gate later phases)

These are investigations, not big PRs. Do them first; each unblocks a design fork.

| ID | Spike | Resolves | Output | → owner |
|---|---|---|---|---|
| **INV-1** | Line-by-line read of `MediaItemCapabilityReferenceProjector`, `AssetStateReferenceProjector`, `MediaItemVersionAssetReferenceProjector`, `AssetProfileDefaultReferenceProjector` | The `XM-H3/H4` (unconditional/last-write-wins) vs sweep-§7d ("looks guarded") contradiction | Confirmed defect list + watermark design → scopes **B3** | Chase |
| **INV-3** | Generate the SNS filter allowlist from `[MessageType]` attributes at synth time? | `XM-DF2` (filter/bridge/DEPLOYMENT.md are 3 hand-maintained copies) | Go/no-go → optional **A4f** | Chase |
| **INV-4** | Product call: build now vs formally defer+feature-gate the MediaItem **review saga** and **DocumentSigning** | `S-05/S-23/XM-C5`, `S-24/XM-C7` | Scope of **Phase 6**; interim gating language for **A4d** | Chase |
| **INV-5** | Confirm the platform store's conditional-write semantics on `EventVersion`/`ProjectedVersion` (several reviews mark this "unverified") | `RG-M6/F-C2`, ref-projector guards | Removes "provisional" tags on B3 + registration projector work | Chase |

> **INV-2 (outbox strategy)** moved to the companion plan `architecture-review-authz-and-outbox-deferred-plan.md` — it scopes the deferred outbox PR (B4) and has no consumer left in this doc.

---

## 7. Phase 1 — Async integration backbone (Stream A)

**Goal:** the choreography actually runs, end-to-end, verified in a live SNS environment. **Order is not optional within this phase.**

### PR-A1 — Production messaging registration + missing publishers ★ROOT
- **Closes:** `S-08 / XM-C1` (no `IMessageBus` in async hosts), `S-09 / XM-C2` (`processingjob.created/scan-result/bypassed` unregistered), `S-10` (started/completed/failed registered in the wrong host).
- **Scope:** one shared `AddMediaProductionMessaging()` extension registering the platform `IMessageBus` + **all** module SNS publishers, called by `ProcessingWorker`, `EventConsumers`, `SagaOrchestrator`, `TimeoutScanner`. Add the three missing Processing publisher registrations. Add a prod publish smoke test (one event per host).
- **Repos:** app (+ platform if the extension belongs in the SDK). **Depends:** none. **Blocks:** all of Phase 1 + `S-22`. **Size:** medium. **Verify:** smoke test publishes from each host without `InvalidOperationException`; A5 covers the real end-to-end. **→ Chase.**

### PR-A2 — SNS-backed test environment + deploy-blocker fix
- **Closes:** `S-11 / XM-C1` (no live env ever publishes cross-host), `XM-M7` (ORGANIZATION_ID placeholder → ECR 403).
- **Scope:** enable an SNS-backed bus in a dedicated non-prod/integration environment (not the `Development` in-process bus) so the chain can be exercised; parameterize `ORGANIZATION_ID` so no placeholder reaches a real deploy.
- **Repos:** cdk + app config. **Depends:** A1 (to have something worth publishing). **Blocks:** A5. **Size:** medium. **→ Chase.**

### PR-A3 — EventConsumers rewire + single-host idempotent job creation
- **Closes:** `S-12 / XM-C4` (`AddProcessingIntegrationEventConsumers` mis-hosted → saga handlers DLQ-loop and take Catalog projections down with them), `S-13 / PJ-H1` (upload-confirmed consumed by two hosts, non-idempotent `ProcessingJobId.New()` per delivery → duplicate jobs/scans/sagas).
- **Scope:** stop registering the saga/worker consumers in `EventConsumers`; keep the saga in `SagaOrchestrator` only. Make ProcessingJob creation single-host + idempotent keyed on `AssetId` (add `GetByAssetIdAsync`, short-circuit on existing). Check the create `Result` before scanning.
- **Repos:** app. **Depends:** A1. **Size:** medium. **Verify:** one upload-confirmed → exactly one job; redelivery → no-op. **→ Chase.**

### PR-A4 — Filter ⇄ bridge reconciliation (paired CDK+code slices)
Each sub-PR pairs a CDK filter edit with its code binding (**P1**). Ship each pair atomically.

| Sub-PR | Closes | Change | Repos |
|---|---|---|---|
| **A4a** | `S-01 / XM-C3` + `S-17` | Add `media.recordtype.published/deprecated` to the cross-module filter **and** register `RecordTypeVersionDetailIndexProjector` in the EventConsumers composition (filter fix alone doesn't restore the seam) | cdk + app |
| **A4b** | `S-02`, `S-03 / XM-C3` | Add `media.asset.archived` + `media.asset.infection-detected` to the filter (`S-03` also needs A1's publisher) | cdk (+A1) |
| **A4c** | `S-04 / XM-C6` | Bind the `AssetAssignedToRole` handler to the bus (`AddMessageHandler<…>`); it's DI-registered but never bridged → DLQ | app |
| **A4e** | `S-06 / XM-H2` | Remove the stray `media.asset.validation-passed` from the cross-module filter (belongs only to `media-sagas`) | cdk |
| **A4d** | `S-05 / XM-C5` (interim) | Until the review saga (Phase 6) exists: either register `submitted-for-review`/`changerequest.created` as an explicit logged no-op **with an alarm**, or feature-gate the review-required publish path OFF so publishes aren't silently accepted-and-dropped. Decision from `INV-4`. | app (+cdk) |
| **A4f** _(opt.)_ | `XM-DF2` | Generate the filter allowlist from `[MessageType]` attributes at synth to stop future drift. Gated on `INV-3`. | cdk |

- **Depends:** A1 (A4b/A4d publishers). **Size:** small each. **Verify:** each event reaches its intended consumer; nothing new lands in a DLQ. **→ Chase.**

### PR-A5 — End-to-end ingestion verification
- **Closes (verifies):** `S-22 / XM` (AssetIngestionSaga dead end-to-end) — confirms the saga starts, advances, times out, and compensates once A1–A4 land.
- **Scope:** integration tests in the A2 environment driving upload→confirm→job→scan→validate→process→complete and the two timeout paths; assert no DLQ growth.
- **Depends:** A1, A2, A3, A4. **Size:** medium. **Gate:** **prod/staging deploys stay disabled until this is green.** **→ Chase.**

---

## 8. Phase 2 — Distributed-systems safety (Stream B)

Starts once **A1** lands; runs concurrently with Phases 3–4. These make consumers and sagas correct under the standard (unordered, at-least-once) queues.

### PR-B1 — Shared consumer contract: result-handling + tenant-from-attribute
- **Closes:** `XM-H1 / S-15` (command `Result` swallowed), `S-16` (per-item catch-and-swallow eats transient faults), `AM H-2/H-3`, `PJ-H2/M3`, `S-14 / XM-H8 / AM F-C4` (TenantId from body, not the SNS attribute).
- **Scope:** a shared consumer base/helper that (a) inspects the dispatch `Result` — idempotent no-op → ACK, retryable → throw → SQS retry/DLQ + metric; (b) builds `SqsExecutionContext` from the SNS message attribute and sources tenant/actor from it. Reload-before-retry for concurrency. Apply to **AssetManagement + Processing** consumers in this PR.
- **Repos:** shared + app. **Depends:** A1. **Size:** medium. **→ Chase.**

### PR-B1b — Apply the consumer contract to the remaining hosts
- **Closes:** `MI-H5/FC1`, `MI-M11/FC2`, `MP-FC2`, `CR-B6`, `COL-FC2` (archive fan-out failure propagation — coordinate with D-COL1), Registration consumer result-handling.
- **Depends:** B1. **Size:** medium. **→ Chase.**

### PR-B2 — Saga optimistic concurrency + timeout-scanner fix
- **Closes:** `S-18 / XM-H9` (`DynamoDbSagaRepository.SaveAsync` is an unconditional `PutItem`; `Version` written, never used as a condition), `XM-M4` (`TimeoutScanner` `remainingTime` snapshot never re-read → safety-buffer abort dead).
- **Scope:** conditional write on `Version` (retry on `ConditionalCheckFailed`); re-read remaining time inside the page loop.
- **Repos:** shared (`Media.Shared.Infrastructure/Sagas`). **Depends:** A1 (to matter at runtime). **Size:** small. **→ Chase.**

### PR-B3 — Reference-projector watermark discipline
- **Closes:** `XM-H3` (capability projector mixes `EventVersion`/`UtcTicks`), `XM-H4` (unconditional upsert/delete, resurrection), `AM H-4/F-R3/F-R5`, `RG-M3/M6/F-C1/F-C2`.
- **Scope:** one monotonic version domain per reference model; reorder-safe tombstones for deletes; explicit `if incoming <= current: skip` guards; confirm-time re-check where an upload-time guard reads an eventually-consistent model. Covers `MediaItemCapabilityReference`, `AssetStateReference`, `MediaItemVersionAssetReference`, `AssetProfileDefaultReference`, Registration `MediaItemReference`.
- **Depends:** **INV-1** (resolve the contradiction first), INV-5. **Size:** medium. **→ Chase.**

> **Deferred, split out:** **PR-B4 — Publish-failure handling / transactional outbox** (`S-25 / XM-DF1/G1`) and its scoping spike **INV-2** now live in the companion plan `architecture-review-authz-and-outbox-deferred-plan.md`. B4 has no dependants inside this doc, so deferring it does not unblock or block any PR here — but note it remains a real dual-write divergence risk and is on the production gate (§16).

> **In-flight, do not re-plan:** name-reservation/counter atomicity (`COL-H6 / FOL-H5 / MI-H4 / MP-H5 / RT-H3`) is owned by `s13-uniqueness-atomicity-remediation-plan.md` (+ its implementation runbook). Its folder-archive-saga work is the mechanism `D-FOL2` builds on.

---

## 9. Phase 3 — Authorization (Stream C) — **DEFERRED to companion plan**

> **Moved out of this doc on 2026-07-20.** The whole authorization stream — **PR-C0** (actor propagation + authz foundation) and the eight per-module enforcement slices **C1–C8** — now lives in `architecture-review-authz-and-outbox-deferred-plan.md`, owned by **Chase**. It is deferred in sequencing only; **authorization is still a hard production gate** (§16, item 4), so it must land before prod/staging re-enable regardless of which doc tracks it.
>
> **What this means for the rest of this plan:** C0 was one of two true blockers in the dependency spine, but it only ever blocked C1–C8 (all now in the companion plan). Nothing in Streams A, B, D, E, F, or G depends on C0, so removing authz from here does not reorder any remaining PR. Two Phase-4 items previously folded authz work into an enforcement slice — those cross-references are re-pointed in §10 (see `D-RT4` and `D-CR3`): each keeps its read-model / projection work here and hands its authz enforcement to the companion plan.

---

## 10. Phase 4 — Module correctness bugs (Stream D)

Vertical slices, parallelizable once B1 exists. (These previously also waited on the authz foundation C0; with authz split into the companion plan, only the two owner-scoping items below coordinate with it — the rest are independent of authz.) Grouped by module; **★ = trivial-but-critical, pull forward.** Sizes and pairings noted.

### AssetManagement
- **D-AM1 ★** — S3 delete-before-guard data loss (`C-1`): call `asset.Delete()` before the S3 delete; quarantine-not-hard-delete on virus (`M-1`); settle soft-vs-hard delete semantics (`L-3 lifecycle`). _small._
- **D-AM2** — read-model completeness: infection projection (`C-3`), version-artifact/reprocess projection gaps (part of the doc's R4), soft-deleted leak in GET/list (`H-8`), `FileSizeBytes` never populated (`H-9`). _small._
- **D-AM3** — role-assignment / delete-lock invariant (`H-1 / A-D1`): item-scoped uploads never get a role → delete-lock silently disabled. **Pairs `D-MI2`** (asset-binding both sides). _small._
- **D-AM4** — multipart completion/abort idempotency wedge (`H-5`, `L-2 bug`) + orphaned-multipart compensation + part-URL TTL (`M-10`). _medium._
- **D-AM5** — standalone upload size ceiling (`H-7`) + real per-owner billing quota accounting, stop mutating the DI singleton (`H-10`) + assign-time quota charge (`M-6`). _medium._
- **D-AM6** — processing-event metadata mapping completeness (`M-5`), rendition retrievability check (`M-12`), poison-enum `TryParse` (`L-3 bug`), `recordedAt` determinism (`A-D2`). _small, batchable._

### Processing
- **D-PJ1 ★** — projector correctness: `Status="Succeeded"` on failed jobs (`PJ-C1`), index writes `Running` for terminal states (`PJ-H4`), `Bypassed` unprojected (`PJ-H3`) + an event×status projector test matrix. _small._
- **D-PJ2** — completion driver: `AssetProcessingWorker.ProcessAsync` is never invoked → capable jobs sit `Running` until saga timeout (`PJ-C2/H5/L-life2`); establish single owner of Start/Bypass. _large. Depends A1 + host-wiring verification._
- **D-PJ3** — _merged into A3_ (single-host idempotent create, `PJ-H1`).
- **D-PJ4** — scan-failure terminal transition (`PJ-M2/L-life1/L-life4`) + idempotent no-op `Complete`/`Fail` on re-delivery (`PJ-M1/L-life3`) + model `Outcome` as enum/VO. _small._
- **D-PJ5** — real virus scan + rendition pipeline (`PJ-H6`, currently `outcome="Passed"` hardcoded + `NotImplementedException`). **Compliance-blocking, large — feature-gate; scope with Phase 6.**

### Catalog — Collection
- **D-COL1** — archive → **read-model-only reversible** fan-out (`COL-C2/FC1`), bounded/checkpointed (`FC3`), failure propagation (`FC2`, via B1b), add `UnarchiveCollection` (`L-Life2`). **Coordinate with `D-FOL2` + the s13 folder-archive-saga + `MI-Life3`.** _large._
- **D-COL2 ★** — summary projector overwrites `CreatedAt`/`UpdatedAt` on `DefaultProfileSet` (`COL-H4`). _trivial._
- **D-COL3** — archived-state mutation guards on the 4 mutators (`COL-H3/D1`) + suppress mutation events on archived (`FP2`). _small._
- **D-COL4** — atomic PATCH / single `UpdateCollection` command (`COL-H5`). _medium. (`COL-H6` reservation = in-flight s13.)_
- **D-COL5** — default-profile published+owner guards (`COL-M1`) + `createdAt` sort GSI (`COL-M5`). _small._

### Catalog — Folder
- **D-FOL1** — move safety: circular-reference guard (`FOL-C2`), cross-collection immutability (`H1`), subtree-height + descendant depth-counter recompute (`H2`). _medium._
- **D-FOL2** — archive cascade rebuild (`FOL-C3/H6/H7/FC1/FC2`): guard root first, single leaf-first pass (no re-dispatch storm), bounded, resumable. **Largely the s13 folder-archive-saga + read-model conversion — build on it, don't fork.** _large._
- **D-FOL3** — `FolderMediaItemsIndex` misses `MediaItemAssignedToFolder`/`Deleted` (`FOL-H3`); registration counter single source of truth + strong-consistency gate (`M3/M4`). **Pairs `D-MI1`.** _small._
- **D-FOL4** — archived-state guards (`FOL-H4/D1`), bulk parent-existence (`H8`), registration-gate vs ADR-006 reconciliation (`M2`). _small._
- **D-FOL5** — creation-lock rework / TTL / documented 503 (`FOL-M5`) + `ExpectedVersion` threading (`M-conc`). _medium._

### Catalog — MediaItem
- **D-MI1** — ADR-006 `active-items` hierarchy counter never maintained (`MI-H1`) → Folder archive gate always passes; + archived-folder admission guard (`H7`). **Enables `D-FOL3`/`D-FOL4` gate.** _medium._
- **D-MI2** — emit `AssetUnassignedFromRole`/`AssetReplacedInRole` integration events (`MI-H2/FP2`); Asset↔item binding is one-sided. **Pairs `D-AM3`.** _medium._
- **D-MI3** — metadata "full-replace" actually merges (`MI-H3/D3`) + conformance partial-resolution + gap-set (not count) compare (`M-5`). **Pairs `D-MP2`.** _medium._
- **D-MI4** — summary/version projector fixes: CollectionId on assign/move, tag-replace-not-append, draft version number (`MI-H6/M1/M2`), version-list v0-sentinel filter + purged-version handler (`M-6/M-7`). _small._
- **D-MI5** — registration-consumer result-handling (`MI-H5`, via B1b) + withdraw lifecycle guard (`M-4/D1`) + suppress spurious `submitted-for-review` on empty-reviewer publish (`M-3/D2/FP1`). _small._
- **D-MI6** — auto-submit empty-reviewer guard (`M-14`) + conformance fanout bounded/checkpointed (`M-12`, shares mechanism with `MP-H3`). _medium._

### Catalog — MediaProfile
- **D-MP1** — compiled-template serialization round-trip: `BareName`/`SuppressedFieldNames` dropped by converter+snapshot (`MP-H1`) **and** compiled fields never projected/surfaced (`MP-H4`). Paired (H4 depends on H1). _medium._
- **D-MP2** — conformance model: remove the publish-block that contradicts ADR-010 "flag never block" (`MP-H2`) + bounded/checkpointed fan-out (`MP-H3`). **Pairs `D-MI3/MI6`.** _medium._
- **D-MP3** — `MediaProfilePublished` snapshot completeness (`MP-H6/FP1`): omits `AssetDefinitions`/`CompiledTemplate`/per-role `MaxFileSizeBytes` that AM/Registration/Signing ref-models consume. **Feeds B3 + downstream — sequence early.** _medium._
- **D-MP4** — summary counts drift (`M-2`), dimension-constraints projection (`M-3`), resumable/idempotent seeding (`M-7`). _small._

### Metadata — RecordType
- **D-RT1 ★** — data-corruption trio: `DraftDiscarded`→`IsDeprecated=true` (`RT-P1`), `FieldDeprecated` marks *all* fields (`RT-P2`), last-field-removal nulls/bricks the draft (`RT-D1`). _small, high value._
- **D-RT2** — deprecation carries `AggregateVersion` as schema version (`RT-I1`) + name-release-on-deprecate (`RT-H3`, note reservation atomicity = s13) + coded errors / `NothingToDeprecate`→`RecordTypeNotPublished` 409 (`RT-D2/ERR1`). _small._
- **D-RT3** — read-model table mis-wire (singular `media-record-type`, `GetById` reads a different table than the projector writes — potential 500) (`RT-INF1`) + aliases write-only, no projector/read-model (`RT-RM1`). Verify names against cdk. _medium._
- **D-RT4** — owner scoping + summary `HasDraft`/`OwnerId`/`PublishedVersion=0` (`RT-Q1/P3/Q2`). Ships the `OwnerId`/summary read-model fields regardless; the RecordType authz enforcement it previously folded into (`C6`) now lives in the companion authz plan — coordinate so the read-model side lands here and enforcement lands there. _small._
- **D-RT5** — capability `Order` de-conflict on attach (`RT-D4`) + force `SourceCapability=null`/`IsDeprecated=false` for client-authored fields (`RT-VAL3`) + field validators (`RT-VAL1/2/4`). _small._

### Registration
- **D-RG1 ★** — inverted document-eligibility guard (`RG-C2`): attach/amend gate on `HasRegistrationCapability` instead of `!HasProcessingCapability` → rejects valid documents, admits processed media. _small, critical._
- **D-RG2** — search indexer (`RG-H1`): `GET /registrations/search` queries an OpenSearch index no projector populates. Build the indexing projector; align index/fields/owner-scope. _large._ **→ Chase.**
- **D-RG3** — status-name reconciliation `SubmissionRecorded` vs `PendingConfirmation` across 4 sources (`RG-D1/L1`) + owner-notes capture (`M-5/D2/M-2`) + reorder-safe ref projector (`RG-M3`, via B3). _medium._

### ChangeRequests
- **D-CR0** — spec reconciliation first (`CR-S1/S2/S3/S5/S6/S7`): the context-overview/read-model/error-catalog still describe the old full-lifecycle reviewer model. **Doc-only but gates module sign-off — do first.** _small._
- **D-CR1** — snapshot drops `_participantIds`+`ReviewSessionId` → every post-snapshot `AddComment` 403 (`CR-B1`, Critical-in-effect) + store comment bodies in a read model not the aggregate/snapshot (`CR-F1`). _medium._
- **D-CR2** — body validation + 4000-char cap + control-char strip (`CR-B2/B3/G6`) + coded author/not-found errors 403/404 (`CR-B5/G3`) + deleted-comment scrub (`CR-B7/G5`). _small._
- **D-CR3** — participant roster projection (`CR-G4`) → read authz (`CR-B4`). The projection ships here (it's a prerequisite the authz read-check needs); the read-authz enforcement (`C8`) now lives in the companion authz plan — land the projection first, then enforcement there. _medium._

---

## 11. Phase 5 — Contract, validation & spec hygiene (Stream E)

Batched cleanups. **References `api-consistency-remediation-plan.md`** (Stages 0–5 substantially done — status codes, URL naming, request/response hygiene, versioning gate); this phase adds only what that plan doesn't already own.

- **E1 — Validators.** FluentValidation on every module's commands/requests so malformed input → 400/422 not 500 (`AM M-7/M-11, COL-M3, FOL-M8, MI-M13, MP-M4, RT-VAL*, RG-H3, CR-G1`). Per-module or one sweep. _medium._
- **E2 — Error contract.** RFC 9457 `errorCode` emission + catalog-coded `DomainError`s + correct 409-vs-422 (`AM A-D4/H-6, COL-M2, FOL-M1, MI-M9, MP-M1, RT-ERR1, RG-M1/M4, CR-B5/G3`). Confirm against api-consistency's error-catalog work; add the missing per-module codes (`DocumentAlreadyAttached`, Metadata section, etc.). _medium._
- **E3 — Spec/wiki reconciliation** (gates the not-yet-built wiki auto-publish): `*IntegrationEvent` vs `*Message` naming everywhere, stale write-model tables (`PJ-M6/M7`, `MP-M8/L*`, `RT-SPEC*`), stale `bounded-context.md` messaging table + `DEPLOYMENT.md` filter (`XM-M6`), per-module payload/field drift. Focused doc PRs. _medium._
- **E4 — Dead code/DTO cleanup** (`RG-L5, COL-L2, FOL-L5, MP-L7, MI-L1, RT-DEAD1`, `CR-F4` implicit-operator mappers → explicit). _small._
- **E5 — Contract-design nits:** `Status` enum overloading `ProcessingStatus`/`AssetStatus` (`XM-M1`), `MediaItemId` dropped from processing events (`XM-M2`), `StorageKey` internal-layout leak across the BC boundary (`XM-M8`), forward-compat/version-branch test (`XM-M5`), routing-string discipline `media.item.version.purged`→`version-purged` (`S-21`), distinct `[MessageType]` for reprocessing (`S-19`), separate document fast-exit signal from real completion so Billing doesn't mis-count (`S-20 / XM-M3 / AM M-8`). _small–medium._

---

## 12. Phase 6 — Deferred choreography features (Stream F)

Product-gated by `INV-4`. Until built, the interim gate from `A4d` keeps the half-wired paths from silently dropping traffic.

- **F1 — MediaItem review saga** + ChangeRequests review event set (`approved/rejected/abandoned`) + `submitted-for-review` consumer (`S-05/XM-C5`) + reviewer commands + 14-day timeout scanner (`XM-G4`) + terminal states (`S-23`). _large._
- **F2 — DocumentSigning** saga + aggregate + integration events + 72-h timeout scanner + `ISecuredSigningApiClient` (`S-24/XM-C7`); or formally remove the half-wired host/queue so it doesn't read as production-ready. _large._
- **F3 — Reprocessing timeout/compensation** for the S12 path (`AM L-1 lifecycle`): reprocessing re-enters `Validating` but the AssetIngestionSaga is terminal per asset → a stalled reprocess is stuck forever. _medium._
- **F4 — Checkout lifecycle** (`MI-Life2`): implement or formally defer; add a review timeout so `PendingApproval` doesn't hang. _medium._
- **F5 — Registration submission timeout/compensation** (`RG-L2`) + `ExpiresAt`/retention driving (`RG-L3`). _medium._

---

## 13. Stream G — Observability (threaded through Phases 1–2)

- **G1** — thread `CorrelationId` end-to-end (SNS attributes already carry it; no host logs it); per-flow + per-saga success/latency metrics, not just DLQ-depth + saga-approaching-timeout alarms (`XM-G3`); "review submitted but thread not created" alarm (`CR-G8`); counter-drift alarm (ties into the s13 reconciliation Lambda). _medium._ Land alongside B1/B2 so the backbone is observable the moment it starts running.

---

## 14. Suggested delivery waves (capacity view)

Reordering-friendly, but this is the shortest safe path with a 3-person team:

1. **Wave 1 (unblock):** Phase 0 spikes · **A1** · the ★ trivials (`D-PJ1, D-RT1, D-RG1, D-COL2, D-AM1`) — all independent of A1 except none block it.
2. **Wave 2 (backbone live):** A2 · A3 · A4a–e · **A5 gate** · B1/B2 · G1.
3. **Wave 3 (safety):** B1b · B3 (post-INV-1).
4. **Wave 4 (module depth):** the D-* clusters, archive-coordination group (`D-COL1 + D-FOL2 + D-MI1 + s13 saga`) sequenced together; `D-MP3` early (feeds B3).
5. **Wave 5 (hygiene + features):** E1–E5 · Phase 6 per product.

> **Deferred, scheduled separately (companion plan):** the authz stream (**C0** then **C1–C8**) and the **B4** outbox PR + **INV-2** spike. C0 has no in-this-doc predecessor and can still start early in parallel; C1–C8 follow C0. Sequence them into the waves above when re-picking them up — both remain on the production gate (§16).

---

## 15. Draft ADO work items (ready to paste — NOT created)

Board: **Media** (its own ADO project) · Area: `magiq-media` · Priority: High. **Assignee: Chase on every item this revision** (re-assign at scheduling time). Tags let you slice by repo/theme. Dependencies use ADO "Predecessor/Successor" links.

**Backlog levels — matched to the Media project's Agile process template** (verified live: Epics → Features → *User Story | Bug* → Tasks). The earlier draft skipped two of these levels; this is the corrected mapping:

- **Epic = work stream** (§5). Set `Business Value` / `Value Area`.
- **Feature = a coherent PR cluster** within a stream (e.g. the whole A4 filter⇄bridge set; the consumer contract; one per module for Stream D). Set `Effort`.
- **User Story _or_ Bug = one per PR** (the items in §7–13) — **this is the level your PRs attach to**, not Task. Rule of thumb: **Bug** when the item fixes a defect in existing code traced to a finding ID (most of Stream D, the seam defects, saga/projector defects); **User Story** for net-new / enabling / verification / cleanup work (test env, consumer contract, search indexer, validators, deferred features, spikes tagged `spike`). Set `Story Points` (map size: _small_≈2, _medium_≈5, _large_≈8–13).
- **Task = sub-step under a Story/Bug** — optional in general, **required for cross-repo PRs: one Task (and one GitHub PR) per repo** so a `cdk`+`app` pair is captured as two Tasks under one Story (see the pattern block after the tables). Set `Remaining Work`.

Create top-down: **Epics → Features → Stories/Bugs → Tasks**, wiring each child's parent as you go, then add Predecessor/Successor links from the **Depends-on** column. A Task parented directly to an Epic (as the old draft did) will not roll up on the backlog or boards — every PR-level item below is a **Story or Bug**, never a bare Task.

> **The Authorization epic and its C0–C8 stories, plus the B4 outbox bug and the INV-2 spike, are NOT in these tables** — they belong to `architecture-review-authz-and-outbox-deferred-plan.md`, drafted there in the same corrected hierarchy. Note the two cross-plan links: B4/INV-2 parent to the **Distributed-systems safety** epic defined here, and companion stories **C6→D-RT4** / **C8→D-CR3** take predecessors from Stream D here.

### Epics
| Title | Type | Tags |
|---|---|---|
| Async integration backbone | Epic | `backbone; messaging; blocker` |
| Distributed-systems safety | Epic | `reliability; consumers; sagas` |
| Module correctness bugs | Epic | `correctness; per-module` |
| Contract, validation & spec hygiene | Epic | `contract; docs; validation` |
| Deferred choreography features | Epic | `feature; deferred; gated` |
| Observability | Epic | `observability` |

### Features (parent = Epic)
| Feature | Parent Epic | Covers | Tags |
|---|---|---|---|
| Spikes & decisions | Async integration backbone | INV-1/3/4/5 | `spike` |
| Messaging backbone & rewire | Async integration backbone | A1–A3 | `messaging` |
| Filter⇄bridge reconciliation | Async integration backbone | A4a–A4f | `cdk;bridge` |
| End-to-end verification | Async integration backbone | A5 | `test;gate` |
| Consumer contract | Distributed-systems safety | B1, B1b | `consumers` |
| Saga & projector safety | Distributed-systems safety | B2, B3 | `sagas;projectors` |
| AssetManagement correctness | Module correctness bugs | D-AM1–6 | `mod:assetmanagement` |
| Processing correctness | Module correctness bugs | D-PJ1/2/4/5 | `mod:processing` |
| Catalog — Collection | Module correctness bugs | D-COL1–5 | `mod:collection` |
| Catalog — Folder | Module correctness bugs | D-FOL1–5 | `mod:folder` |
| Catalog — MediaItem | Module correctness bugs | D-MI1–6 | `mod:mediaitem` |
| Catalog — MediaProfile | Module correctness bugs | D-MP1–4 | `mod:mediaprofile` |
| Metadata — RecordType | Module correctness bugs | D-RT1–5 | `mod:recordtype` |
| Registration | Module correctness bugs | D-RG1–3 | `mod:registration` |
| ChangeRequests | Module correctness bugs | D-CR0–3 | `mod:changerequests` |
| Contract & hygiene | Contract, validation & spec hygiene | E1–E5 | `contract;docs` |
| Deferred features | Deferred choreography features | F1–F5 | `feature;gated` |
| Observability | Observability | G1 | `observability` |

### User Stories / Bugs (parent = Feature) — one per PR
Type per the rule above (**Bug** = defect fix traced to a finding; **Story** = net-new/enabling/verification/spike). Streams A, B, G enumerated; Stream D/E/F enumerated by rule below. Assignee = **Chase** throughout.

| Item | Type | Parent Feature | Findings | Depends-on | Repo(s) |
|---|---|---|---|---|---|
| INV-1 ref-projector contradiction | Story `spike` | Spikes & decisions | XM-H3/H4 | — | app |
| INV-3 filter-gen feasibility | Story `spike` | Spikes & decisions | XM-DF2 | — | cdk |
| INV-4 review-saga / signing defer call | Story `spike` | Spikes & decisions | S-05/23/24 | — | — |
| INV-5 store conditional-write semantics | Story `spike` | Spikes & decisions | RG-M6/F-C2 | — | platform |
| A1 Production messaging + missing publishers | **Bug** | Messaging backbone & rewire | S-08/09/10 | — | app (+platform) |
| A2 SNS test env + ORG_ID fix | Story | Messaging backbone & rewire | S-11, XM-M7 | A1 | **cdk + app** → 2 Tasks |
| A3 EventConsumers rewire + idempotent create | **Bug** | Messaging backbone & rewire | S-12/13, PJ-H1 | A1 | app |
| A4a recordtype filter + projector | **Bug** | Filter⇄bridge reconciliation | S-01/17 | A1 | **cdk + app** → 2 Tasks |
| A4b asset.archived/infection filter | **Bug** | Filter⇄bridge reconciliation | S-02/03 | A1 | cdk |
| A4c bind asset-assigned handler | **Bug** | Filter⇄bridge reconciliation | S-04 | A1 | app |
| A4e drop stray validation-passed | **Bug** | Filter⇄bridge reconciliation | S-06 | A1 | cdk |
| A4d review-path interim gate | Story | Filter⇄bridge reconciliation | S-05 | INV-4 | **app + cdk** → 2 Tasks |
| A4f filter-gen from attributes _(opt.)_ | Story | Filter⇄bridge reconciliation | XM-DF2 | INV-3 | cdk |
| A5 end-to-end ingestion verification | Story | End-to-end verification | S-22 | A1–A4 | app |
| B1 consumer contract: result+tenant | Story | Consumer contract | XM-H1/H8, S-14/15/16 | A1 | shared + app |
| B1b consumer contract rollout | Story | Consumer contract | MI-H5, MP-FC2, CR-B6, COL-FC2 | B1 | app |
| B2 saga OCC + timeout-scanner | **Bug** | Saga & projector safety | S-18, XM-M4 | A1 | shared |
| B3 reference-projector watermarks | **Bug** | Saga & projector safety | XM-H3/H4, AM-H4, RG-M3 | INV-1 | app |
| G1 observability | Story | Observability | XM-G3, CR-G8 | B1 | app |

**Stream D (Module correctness) — one Story/Bug per PR in §10, parented to that module's Feature.** Default type **Bug** (they're finding-traced defect fixes). Type **Story** exceptions: `D-PJ2` (completion driver — net-new), `D-PJ5` (real scan/rendition pipeline — net-new, feature-gated), `D-RG2` (search indexer — net-new), `D-CR0` (spec reconciliation — `docs`). Depends-on: `B1` for the consumer-contract-dependent items (`D-MI5`, `D-COL1`), otherwise per §10 pairings; the archive-coordination cluster (`D-COL1 + D-FOL2 + D-MI1`) links to the s13 saga.

**Stream E (Contract & hygiene) — E1–E5 as Stories** (tech-debt/chore) under the *Contract & hygiene* Feature, per §11. **Stream F (Deferred features) — F1–F5 as Stories** (`feature;gated`) under *Deferred features*, all with predecessor `INV-4`, per §12.

### Cross-repo pattern — Story + one Task/PR per repo
Where an item touches two repos, create the **Story once** and a **Task per repo**; each Task gets its own GitHub PR on branch `feature/chase/<task-ticket>-<slug>`, both PRs citing `AB#<story-id>`, landing behind one merge gate (**P1**):

- **A2** → Task `cdk: SNS-backed bus + parameterise ORGANIZATION_ID` (`cdk-magiq-media`) + Task `app: integration-env messaging config` (`magiq-media`).
- **A4a** → Task `cdk: add media.recordtype.published/deprecated to filter` + Task `app: register RecordTypeVersionDetailIndexProjector`.
- **A4d** → Task `app: interim gate/feature-flag on review publish` + Task `cdk: alarm + filter no-op` (shape per INV-4).

> **Deferred to the companion plan (not created from this doc):** the Authz epic + its Features/Stories (C0–C8), the B4 publish-failure/outbox **Bug**, and the INV-2 spike — drafted there in this same Epic→Feature→Story/Bug→Task shape.

> Say the word and I'll enumerate every Stream D/E/F Story/Bug in full (≈40 rows) with per-PR descriptions and the predecessor links wired — or create the whole tree on the Media board top-down.

---

## 16. What must be true before re-enabling prod/staging

A hard gate, restating the reviews' "Top 5 before production" consensus mapped to this plan:

1. **A1 + A2 + A5** — backbone lands and the full ingestion chain is verified in a live SNS environment (`XM-C1/C2`, `S-08/09/22`).
2. **A3 + A4** — EventConsumers mis-wiring fixed; filter⇄bridge reconciled; nothing silently dropped or DLQ-looping (`XM-C3/C4/C5/C6`).
3. **B1 + B2 + B3** — consumers inspect `Result`; sagas have optimistic concurrency; reference projectors are reorder-safe (`XM-H1/H9/H3/H4`).
4. **C0 + C1–C8** — authorization enforced in every module; the Registration System-actor and MediaItem purge gates in particular (`*-C1/C2`, `RG-C1`). **Now tracked in the companion plan `architecture-review-authz-and-outbox-deferred-plan.md` — deferred in sequencing, but not waived: this remains a hard pre-prod gate.**
5. **The ★ correctness bugs** — `PJ-C1`, `RT-P1/P2/D1`, `RG-C2`, `AM C-1`, `C-3` — landed and covered by tests.

Everything past that gate is quality-and-completeness work that can ship continuously post-launch. **One strongly-recommended addition carried in the companion plan:** the publish-failure/outbox work (**B4**) closes a durable dual-write divergence (`S-25`); close it before prod if the async volume makes silent publish loss material.

---

_Prepared as a planning artifact over the 2026-07-19 review set. Finding IDs and severities are the reviews'; sequencing, PR grouping, and ADO shaping are this plan's. Cross-references to `s13-uniqueness-atomicity-remediation-plan.md`, `api-consistency-remediation-plan.md`, and `content-category-remediation-plan.md` are load-bearing — check those before opening a PR that touches reservation atomicity, the API error/DTO contract, or media categories._
