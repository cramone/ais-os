# Architecture-Review Remediation — ADO Work-Item Index

_Media project (dev.azure.com/MAGIQSoftware, project "Media"). Created 2026-07-20 from architecture-review-remediation-pr-plan.md. **Status: COMPLETE** — all items created, parent-linked, and dependency-linked. Owner/assignee context: Chase. Tag on Epics: `arch-review-remediation`._

Totals: **6 Epics · 18 Features · 71 User Stories/Bugs · 74 Tasks** (169 work items) · **30 predecessor/successor dependency links**. This index supersedes `ado-creation-resume-manifest.md` (now historical).

Open any item at: `https://dev.azure.com/MAGIQSoftware/Media/_workitems/edit/<id>`

## Epics
| Key | ID | Title |
|---|---|---|
| A | 34275 | Async integration backbone |
| B | 34276 | Distributed-systems safety |
| D | 34277 | Module correctness bugs |
| E | 34278 | Contract, validation & spec hygiene |
| F | 34279 | Deferred choreography features |
| G | 34280 | Observability |

## Features (parent Epic)
| Feature | ID | Epic |
|---|---|---|
| A-F1 Spikes & decisions | 34281 | 34275 |
| A-F2 Messaging backbone & rewire | 34282 | 34275 |
| A-F3 Filter⇄bridge reconciliation | 34283 | 34275 |
| A-F4 End-to-end verification | 34284 | 34275 |
| B-F1 Consumer contract | 34285 | 34276 |
| B-F2 Saga & projector safety | 34286 | 34276 |
| G-F1 Observability | 34287 | 34280 |
| E-F1 Contract & hygiene | 34288 | 34278 |
| F-F1 Deferred features | 34289 | 34279 |
| D-F-AM AssetManagement correctness | 34290 | 34277 |
| D-F-PJ Processing correctness | 34291 | 34277 |
| D-F-COL Catalog — Collection | 34292 | 34277 |
| D-F-FOL Catalog — Folder | 34293 | 34277 |
| D-F-MI Catalog — MediaItem | 34294 | 34277 |
| D-F-MP Catalog — MediaProfile | 34295 | 34277 |
| D-F-RT Metadata — RecordType | 34296 | 34277 |
| D-F-RG Registration | 34297 | 34277 |
| D-F-CR ChangeRequests | 34298 | 34277 |

## Stories/Bugs & their Task children
Format: `Key = itemID (taskID)`; cross-repo items list both tasks.

**A-F1 (34281):** INV-1 = 34336 (34338) · INV-3 = 34341 (34344) · INV-4 = 34346 (34349) · INV-5 = 34351 (34354)
**A-F2 (34282):** A1 = 34301 (34334) · A2 = 34358 (cdk 34359, app 34362) · A3 = 34366 (34368)
**A-F3 (34283):** A4a = 34372 (cdk 34375, app 34378) · A4b = 34380 (34382) · A4c = 34384 (34386) · A4e = 34388 (34390) · A4d = 34392 (app 34393, cdk 34394) · A4f = 34395 (34396)
**A-F4 (34284):** A5 = 34397 (34398)
**B-F1 (34285):** B1 = 34306 (34312) · B1b = 34308 (34313)
**B-F2 (34286):** B2 = 34302 (34315) · B3 = 34305 (34316)
**G-F1 (34287):** G1 = 34309 (34317)
**E-F1 (34288):** E1 = 34299 (34339) · E2 = 34343 (34347) · E3 = 34350 (34353) · E4 = 34356 (34361) · E5 = 34364 (34367)
**F-F1 (34289):** F1 = 34370 (34373) · F2 = 34376 (34379) · F3 = 34381 (34383) · F4 = 34385 (34387) · F5 = 34389 (34391)
**D-F-AM (34290):** D-AM1 = 34300 (34303) · D-AM2 = 34307 (34404) · D-AM3 = 34310 (34407) · D-AM4 = 34311 (34409) · D-AM5 = 34314 (34411) · D-AM6 = 34318 (34412)
**D-F-PJ (34291):** D-PJ1 = 34319 (34414) · D-PJ2 = 34321 (34417) · D-PJ4 = 34320 (34415) · D-PJ5 = 34322 (34419)
**D-F-COL (34292):** D-COL1 = 34323 (34420) · D-COL2 = 34324 (34422) · D-COL3 = 34325 (34424) · D-COL4 = 34326 (34425) · D-COL5 = 34327 (34427)
**D-F-FOL (34293):** D-FOL1 = 34399 (34400) · D-FOL2 = 34401 (34402) · D-FOL3 = 34403 (34405) · D-FOL4 = 34406 (34408) · D-FOL5 = 34410 (34413)
**D-F-MI (34294):** D-MI1 = 34416 (34418) · D-MI2 = 34421 (34423) · D-MI3 = 34426 (34428) · D-MI4 = 34431 (34432) · D-MI5 = 34433 (34434) · D-MI6 = 34435 (34436)
**D-F-MP (34295):** D-MP1 = 34437 (34438) · D-MP2 = 34439 (34440) · D-MP3 = 34441 (34442) · D-MP4 = 34443 (34444)
**D-F-RT (34296):** D-RT1 = 34304 (34429) · D-RT2 = 34329 (34430) · D-RT3 = 34330 (34331) · D-RT4 = 34332 (34333) · D-RT5 = 34335 (34337)
**D-F-RG (34297):** D-RG1 = 34340 (34342) · D-RG2 = 34345 (34348) · D-RG3 = 34352 (34355)
**D-F-CR (34298):** D-CR0 = 34357 (34360) · D-CR1 = 34363 (34365) · D-CR2 = 34369 (34371) · D-CR3 = 34374 (34377)

## Dependency links (Predecessor → Successor)
- A1 (34301) precedes: A2, A3, A4a, A4b, A4c, A4e, A5, B1, B2, D-PJ2
- INV-4 (34346) precedes: A4d, F1, F2, F3, F4, F5
- INV-3 (34341) precedes: A4f
- INV-1 (34336) + INV-5 (34351) precede: B3
- B1 (34306) precedes: B1b, G1, D-COL1, D-MI5
- A2, A3, A4a, A4b, A4c, A4e, A4d all precede: A5 (the deploy-re-enable gate)

## Notes / follow-ups
- **Types:** finding-traced defect fixes are **Bugs**; spikes, enabling/net-new, verification, hygiene and deferred-feature items are **User Stories** (per the plan's rule).
- **Placeholder custom fields:** this project's Bug/User-Story templates require custom fields (User, User Permissions, On Premise or Cloud=Cloud, Affected Customer, Describe the bug, Replication Steps, Expected Results). These were filled with finding-derived text and the placeholder `Affected Customer = "Internal — Media platform architecture-review remediation"`. Replace if your team reports on those fields.
- **Branch/PR linking:** use `feature/chase/<workItemId>-<slug>` and cite `AB#<workItemId>` in each GitHub PR (Azure Boards GitHub app must be installed) — see the plan §3.
- **Deferred (not on the board):** Authorization (C0–C8) and the outbox (B4/INV-2) remain in `architecture-review-authz-and-outbox-deferred-plan.md`.
