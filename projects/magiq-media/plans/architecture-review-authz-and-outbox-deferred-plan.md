# Authorization + Transactional-Outbox — Deferred Remediation Plan

_magiq-media · Companion to `architecture-review-remediation-pr-plan.md`._
_Author: architecture pass (AI-assisted), for Chase Ramone · Split out 2026-07-20._
_Status: **DEFERRED — parked, not cancelled.** Owner: **Chase** on every item. ADO items **drafted here, not created**._

> **Why this doc exists.** On 2026-07-20 the authorization stream (**Stream C / Phase 3**) and the transactional-outbox PR (**PR-B4**), plus the outbox scoping spike (**INV-2**), were pulled out of the main remediation plan so the primary backlog stays focused on the async backbone (Phase 1), distributed-systems safety (Phase 2 minus outbox), and per-module correctness (Phase 4). **Deferred means sequencing only — both remain hard/near-hard pre-production obligations.** Authorization is explicitly on the production gate (`main plan §16, item 4`); the outbox work closes a durable dual-write divergence that should land before prod if async volume makes silent publish loss material.

> **Finding IDs and severities are the reviews'** (the 2026-07-19 set in `D:\source\github\magiq-media\docs\reviews\`); sequencing and PR grouping are this plan's, unchanged from the main plan except for ownership (now all **Chase**) and being tracked here.

---

## 1. Scope of this deferred plan

| Item | Was | Nature | Prod gate? |
|---|---|---|---|
| **INV-2** | main §6 Phase 0 spike | Outbox strategy decision — scopes B4 | scopes B4 |
| **PR-B4** | main §8 Stream B | Publish-failure handling / transactional outbox | strongly-recommended pre-prod |
| **PR-C0** | main §9 Stream C | Actor propagation + authorization foundation | **yes — §16.4** |
| **PR-C1–C8** | main §9 Stream C | Per-module authorization enforcement (8 slices) | **yes — §16.4** |

Everything else in the main plan is unchanged and does **not** depend on any item here (C0 only ever blocked C1–C8; B4 had no dependants in the main doc).

---

## 2. Phase 0 spike — INV-2 (outbox strategy)

| ID | Spike | Resolves | Output | → owner |
|---|---|---|---|---|
| **INV-2** | Outbox strategy: the platform ships one, but it enqueues in a separate write from the event append | `S-25 / XM-DF1/G1` | Decision: fail-command vs relay vs `TransactWriteItems` spanning events+outbox → scopes **B4** | Chase |

Do this before B4; the decision determines B4's size and shape. INV-5 (store conditional-write semantics, in the main plan) is a useful input if the chosen strategy leans on a conditional transactional write.

---

## 3. Transactional outbox (from main Stream B)

### PR-B4 — Publish-failure handling / transactional outbox
- **Closes:** `S-25 / XM-DF1/G1` (dual-write: SNS publish after event-store append is fire-and-log; failed publish = durably-stored-but-never-published divergence).
- **Scope:** per `INV-2` — at minimum fail the command (or enqueue) on publish failure; strategically wire the platform outbox relay. Note the outbox itself is a second write unless a single `TransactWriteItems` spans events + outbox.
- **Depends:** INV-2. **Also relevant:** A1 (there must be a live publisher for a publish to fail) and INV-5. **Size:** medium–large. **→ Chase.**

> **Sequencing note:** B4 is most valuable once the async backbone (main Phase 1, `A1`/`A2`/`A5`) is live and actually publishing — a divergence you can't yet produce is hard to test. Pick it up alongside or just after Phase 2 safety work (B1/B2/B3).

---

## 4. Authorization (main Phase 3 / Stream C)

The single largest cross-cutting theme: **8 module Criticals of the same shape** (no ownership check, no actor threaded, privileged reads/writes open to any tenant user). One foundation, eight thin enforcement slices.

### PR-C0 — Actor propagation + authorization foundation ★
- **Closes (enables):** the shared half of `C-2, COL-C1, FOL-C1, MI-C1/C2, MP-C1, RT-H1, RG-C1, CR-B4`.
- **Scope:** thread `ActorId`/`ActorType` from `IExecutionContext` into command dispatch; shared helpers for owner-check (`actor.Id == OwnerId` → 403 `NotResourceOwner`) and System-actor assertion (→ 403 `SystemActorRequired`); System-dispatched commands exempt; map to RFC 9457 `errorCode`.
- **Repos:** platform + shared. **Depends:** none (can start immediately, parallel to the main plan's Phase 1). **Blocks:** C1–C8. **Size:** medium. **→ Chase.**

Each per-module PR below enforces authz **and** folds in that module's owner-scoped reads + `TenantId`-leak DTO removal (same surface, one touch). All **depend on C0.**

| PR | Module | Closes | Notes | → owner |
|---|---|---|---|---|
| **C1** | AssetManagement | `C-2`, `M-9` (TenantId leak), download-URL protection | Presigned GET currently open to any tenant user | Chase |
| **C2** | Collection | `COL-C1/H1/H2`, `M-4`, `M-6` | Reconcile `/collections/public` anon-vs-authed (`M-6`) | Chase |
| **C3** | Folder | `FOL-C1`, `M-6` | Also: create must load Collection, copy its `OwnerId`, check write-access (owner-from-caller bug) | Chase |
| **C4** | MediaItem | `MI-C1`, `MI-C2` (System-gate the GDPR purge), `M-10` | Purge releases VersionArtifact S3 protection — must be System/admin only | Chase |
| **C5** | MediaProfile | `MP-C1`, `MP-M6`, `MP-M5` | `owner_system` shared defaults readable by all; writes owner-only | Chase |
| **C6** | RecordType | `RT-H1`, `RT-Q1/Q2`, `RT-P3` | Needs `OwnerId` on summary + owner index; folds RT read-scoping. **Coordinate with main-plan `D-RT4`**, which ships the `OwnerId`/summary read-model fields | Chase |
| **C7** | Registration | `RG-C1`, `RG-H4` | **Two** checks: owner on 6 handlers; `ActorType==System` on the 5 system handlers (self-confirm = authority-reference forgery) | Chase |
| **C8** | ChangeRequests | `CR-B4`, `CR-G4` (participant projection) | Read authz needs the participant roster projected first — **main-plan `D-CR3` ships that projection**; enforce here on top | Chase |

> **Cross-doc dependencies to watch:** `C6` pairs with main-plan `D-RT4` (read-model fields land there, enforcement here) and `C8` pairs with main-plan `D-CR3` (participant roster projection lands there, read-authz here). Land the read-model/projection halves in the main plan first, then the enforcement slices here.

---

## 5. Dependency picture

```
  C0 actor+authz foundation ★  (no predecessor — can start any time)
        └─► C1 .. C8 per-module enforcement  (each needs C0)
                 C6 ⇄ main-plan D-RT4 (read-model fields)
                 C8 ⇄ main-plan D-CR3 (participant projection)

  INV-2 outbox strategy ─► B4 publish-failure / outbox
        (B4 best exercised after main Phase 1 backbone is live)
```

Nothing here blocks the main plan; the main plan's `A1` (live publishing) is a practical precondition for meaningfully testing B4.

---

## 6. Suggested pick-up order

1. **C0** early and in parallel — it has no predecessor and unblocks all eight enforcement slices. Starting it alongside the main plan's Phase 1 keeps authz off the critical path later.
2. **C1–C8** after C0, sequencing `C6`/`C8` after their main-plan read-model/projection halves (`D-RT4`/`D-CR3`) land.
3. **INV-2** whenever, then **B4** alongside/after the main plan's Phase 2 safety work, once the backbone is live enough to produce and test a publish-failure divergence.

---

## 7. Draft ADO work items (ready to paste — NOT created)

Board: **Media** (its own ADO project) · Area: `magiq-media` · Priority: High. **Assignee: Chase on every item** (re-assign at scheduling time). Dependencies use ADO "Predecessor/Successor" links.

**Same corrected hierarchy as the main plan** (Media runs the Agile template: Epics → Features → *User Story | Bug* → Tasks). PR-level items are **Stories/Bugs**, never bare Tasks; Tasks are sub-steps (one per repo for cross-repo work). Create top-down and wire parents as you go.

### Epic
| Title | Type | Tags |
|---|---|---|
| Authorization | Epic | `security; authz; cross-cutting; deferred` |

_(No new outbox epic — the outbox work parents to the **Distributed-systems safety** epic defined in the main plan.)_

### Features
| Feature | Parent Epic | Covers | Tags |
|---|---|---|---|
| Authz foundation | Authorization | C0 | `security;platform` |
| Per-module authz enforcement | Authorization | C1–C8 | `security` |
| Publish reliability / outbox | Distributed-systems safety _(main plan)_ | INV-2, B4 | `messaging;outbox` |

### User Stories / Bugs (parent = Feature) — one per PR
| Item | Type | Parent Feature | Findings | Depends-on | Repo(s) |
|---|---|---|---|---|---|
| INV-2 outbox strategy | Story `spike` | Publish reliability / outbox | S-25 | — | app / platform |
| B4 publish-failure / outbox | **Bug** | Publish reliability / outbox | S-25 | INV-2 | shared + app |
| C0 actor propagation + authz foundation | Story | Authz foundation | shared authz | — | platform + shared |
| C1 AssetManagement authz | **Bug** | Per-module authz enforcement | C-2, M-9 | C0 | app |
| C2 Collection authz | **Bug** | Per-module authz enforcement | COL-C1/H1/H2/M4/M6 | C0 | app |
| C3 Folder authz | **Bug** | Per-module authz enforcement | FOL-C1/M6 | C0 | app |
| C4 MediaItem authz (+purge) | **Bug** | Per-module authz enforcement | MI-C1/C2/M10 | C0 | app |
| C5 MediaProfile authz | **Bug** | Per-module authz enforcement | MP-C1/M5/M6 | C0 | app |
| C6 RecordType authz (+scoping) | **Bug** | Per-module authz enforcement | RT-H1/Q1/Q2/P3 | C0, **D-RT4** _(main)_ | app |
| C7 Registration authz (+System) | **Bug** | Per-module authz enforcement | RG-C1/H4 | C0 | app |
| C8 ChangeRequests authz (+participants) | **Bug** | Per-module authz enforcement | CR-B4/G4 | C0, **D-CR3** _(main)_ | app |

> **Cross-plan links:** the *Publish reliability / outbox* Feature parents to the main plan's **Distributed-systems safety** epic; **C6** and **C8** take predecessors from the main plan's Stream D (**D-RT4**, **D-CR3**) — those read-model/projection halves land in the main plan first, enforcement here.

---

## 8. Production-gate reminder

From the main plan's §16 ("What must be true before re-enabling prod/staging"):

- **Item 4 — `C0 + C1–C8`:** authorization enforced in every module; the Registration System-actor and MediaItem purge gates in particular (`*-C1/C2`, `RG-C1`). **Hard gate — deferring the work does not waive the gate.**
- **Outbox (`B4`, `S-25`):** strongly-recommended pre-prod; close it before prod if async volume makes silent publish loss material.

_Deferral is a scheduling decision, not a downgrade in severity. When these are picked back up, fold them into the main plan's delivery waves (§14) or schedule them as their own wave._
