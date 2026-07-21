# ADO Work-Item Creation — Resume Manifest

_Media project (dev.azure.com/MAGIQSoftware, project "Media", id 85df5236-7642-447d-8088-a4d30099cc90)._
_Created from architecture-review-remediation-pr-plan.md · 2026-07-20. Paused mid-run: the Azure DevOps connector went unavailable after the Epics/Features and part of the Stories were created._

## Why it paused
The Azure DevOps MCP connector (locally installed, proxied through device `ramonehome`) returned **"Server azure-devops unavailable"** mid-run and stayed down. The device bridge itself is fine (file tools work) — only the ADO connector needs a **restart/reconnect in the Claude desktop app**. No cloud-vs-computer re-run needed.

## CRITICAL schema note for resume
`wit_add_child_work_items` **cannot** create Bug or User Story items in this project — those types require custom fields it can't set. Use **`wit_create_work_item`** with `System.Parent` set (one call, also does the parent link). Required fields:
- **User Story:** `Custom.AffectedCustomer`
- **Bug:** `Custom.AffectedCustomer`, `Custom.Describethebug`, `Custom.ReplicationSteps`, `Custom.Expectedresults`, `Custom.User`, `Custom.UserPermissions`, `Custom.OnPremiseorCloud` (picklist — `"Cloud"` is valid)
- **Task:** no custom fields required (add_child works, or create_work_item + System.Parent)
Suggested placeholder values: AffectedCustomer=`"Internal — architecture-review remediation"`, User=`"System/Internal"`, UserPermissions=`"N/A"`, OnPremiseorCloud=`"Cloud"`, Describethebug/ReplicationSteps/Expectedresults = the finding summary.

## CREATED — Epics (6, confirmed)
| Key | ID | Title |
|---|---|---|
| A | 34275 | Async integration backbone |
| B | 34276 | Distributed-systems safety |
| D | 34277 | Module correctness bugs |
| E | 34278 | Contract, validation & spec hygiene |
| F | 34279 | Deferred choreography features |
| G | 34280 | Observability |

## CREATED — Features (18, confirmed, linked to their Epic)
| Key | ID | Parent Epic |
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

## CREATED — Stories/Bugs & Tasks

### Fully done (B + G) — items + tasks, parent links confirmed
| Item | Type | ID | Parent Feat | Task ID |
|---|---|---|---|---|
| B1 | Story | 34306 | 34285 | 34312 |
| B1b | Story | 34308 | 34285 | 34313 |
| B2 | Bug | 34302 | 34286 | 34315 |
| B3 | Bug | 34305 | 34286 | 34316 |
| G1 | Story | 34309 | 34287 | 34317 |

### Created but parent link UNCONFIRMED (verify on resume)
| Item | Type | ID | Should parent to | Task |
|---|---|---|---|---|
| A1 | Bug | 34301 | 34282 (A-F2) | none yet |
| E1 | Story | 34299 | 34288 (E-F1) | none yet |
| D-AM1 | Bug | 34300 | 34290 | 34303 (verify link) |
| D-AM2 | Bug | 34307 | 34290 | none |
| D-AM3 | Bug | 34310 | 34290 | none |
| D-AM4 | Bug | 34311 | 34290 | none |
| D-AM5 | Bug | 34314 | 34290 | none |
| D-AM6 | Bug | 34318 | 34290 | none |
| D-PJ1 | Bug | 34319 | 34291 | none |
| D-PJ4 | Bug | 34320 | 34291 | none |
| D-PJ2 | Story | 34321 | 34291 | none |
| D-PJ5 | Story | 34322 | 34291 | none |
| D-COL1 | Bug | 34323 | 34292 | none |
| D-COL2 | Bug | 34324 | 34292 | none |
| D-COL3 | Bug | 34325 | 34292 | none |
| D-COL4 | Bug | 34326 | 34292 | none |
| D-COL5 | Bug | 34327 | 34292 | none |
| D-RT1 | Bug | 34304 | 34296 | none |

### Possible/uncertain
- **INV-1** (User Story, parent 34281) — a create call was in flight when the connector dropped; **existence unknown**. Query by title "INV-1 —" in project Media before recreating to avoid a duplicate.

## NOT YET CREATED — Stories/Bugs to create (parent → task)
Create as User Story unless marked Bug; one Task each (cross-repo items get 2 Tasks). Full titles/descriptions/finding IDs are in architecture-review-remediation-pr-plan.md §6–§13.

- **A-F1 (34281):** INV-1 (if not already), INV-3, INV-4, INV-5 — all User Story
- **A-F2 (34282):** A2 (Story, 2 tasks cdk+app), A3 (Bug)
- **A-F3 (34283):** A4a (Bug, 2 tasks cdk+app), A4b (Bug), A4c (Bug), A4e (Bug), A4d (Story, 2 tasks app+cdk), A4f (Story)
- **A-F4 (34284):** A5 (Story)
- **E-F1 (34288):** E2, E3, E4, E5 — all User Story (E1 already created — 34299)
- **F-F1 (34289):** F1, F2, F3, F4, F5 — all User Story
- **D-F-FOL (34293):** D-FOL1..D-FOL5 — all Bug
- **D-F-MI (34294):** D-MI1..D-MI6 — all Bug
- **D-F-MP (34295):** D-MP1..D-MP4 — all Bug
- **D-F-RT (34296):** D-RT2, D-RT3, D-RT4, D-RT5 — all Bug (D-RT1 already — 34304)
- **D-F-RG (34297):** D-RG1 (Bug), D-RG2 (Story), D-RG3 (Bug)
- **D-F-CR (34298):** D-CR0 (Story), D-CR1 (Bug), D-CR2 (Bug), D-CR3 (Bug)

## NOT YET CREATED — Tasks
One Task per Story/Bug (detailed steps in the plan). Cross-repo items get **two** Tasks:
- A2 → `A2 · task cdk`, `A2 · task app`
- A4a → `A4a · task cdk`, `A4a · task app`
- A4d → `A4d · task app`, `A4d · task cdk`
All other Stories/Bugs → one Task each. Still needed: every item except B1/B1b/B2/B3/G1 (done) and D-AM1 (has 34303).

## FINAL PASS — Predecessor/Successor dependency links (none created yet)
Use `wit_work_items_link` type `predecessor` (id = the dependent item, linkToId = the thing it depends on) once all IDs exist:
- A2 ← A1 · A3 ← A1 · A4a ← A1 · A4b ← A1 · A4c ← A1 · A4e ← A1 · A4d ← INV-4 · A4f ← INV-3
- A5 ← A1, A2, A3, A4a, A4b, A4c, A4d, A4e
- B1 ← A1 · B1b ← B1 · B2 ← A1 · B3 ← INV-1, INV-5 · G1 ← B1
- D-PJ2 ← A1 · D-COL1 ← B1 · D-MI5 ← B1
- F1 ← INV-4 · F2 ← INV-4 · F3 ← INV-4 · F4 ← INV-4 · F5 ← INV-4
- Cross-plan (when companion authz items exist): C6 ← D-RT4 (34...) · C8 ← D-CR3
- External note (no link): D-FOL2 builds on the s13 folder-archive-saga.

## Resume checklist
1. Reconnect the Azure DevOps connector in the desktop app; probe with `wit_get_work_item(34282, expand:relations)`.
2. Verify/repair the UNCONFIRMED parent links (table above) via `wit_work_items_link` type `parent` (id=child, linkToId=feature).
3. Dedup-check INV-1, then create the NOT-YET-CREATED Stories/Bugs (create_work_item + System.Parent + required custom fields).
4. Create all missing Tasks (parent = their Story/Bug).
5. Wire the predecessor links.
6. Verify: each Feature has children; counts ≈ 6 Epics / 18 Features / ~63 Stories+Bugs / ~66 Tasks.
