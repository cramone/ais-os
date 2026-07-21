# magiq-media Remediation — Cowork Execution Instructions

_Standalone operating brief for a Claude Cowork project that executes the architecture-review remediation. Give Claude this file at the start of any execution session. It tells Claude how to **start**, **continue**, and **end** the work._

> **This file is the entry point. The live tracker is `IMPLEMENTATION-PLAN.md` in this same folder — that is the source of truth for what's done and what's next. This file tells you how to operate; that file tells you the state.**

---

## 0. First 5 minutes of any session (do this every time)

1. **Read, in order:**
   - This file (`COWORK-EXECUTION-INSTRUCTIONS.md`) — how to operate.
   - `IMPLEMENTATION-PLAN.md` — the live tracker. Read §9 **Session log** (last entries) and the **Status** columns in §5 to see where we are.
   - `D:\source\github\magiq-media\CLAUDE.md` — repo conventions. **Mandatory before any code or spec edit.**
2. **Confirm access** (see §1 below). If a path or tool is missing, stop and tell the operator — do not improvise.
3. **Announce state:** in one or two lines, say what's `In Progress`, what's the next ready item (§5 order in the plan), and what you intend to do this session. Wait for the operator's "go" if a branch needs creating (branches are operator-created — see §3).

---

## 1. Prerequisites & access check

| Need | Where | Check |
|---|---|---|
| Live tracker + companion docs | `Z:\claudia\magiq\projects\magiq-media\plans\` | `IMPLEMENTATION-PLAN.md` opens |
| App repo (code + `docs\spec\` + `docs\adrs\`) | `D:\source\github\magiq-media` | `git status` works; on/near `develop` |
| CDK repo | `D:\source\github\cdk-magiq-media` | `git status` works |
| Platform SDK repo | `D:\source\github\aspnetcore-platform` | only for A1 / INV-5 |
| ADO work items | `dev.azure.com/MAGIQSoftware`, project **Media** | `azure-devops` MCP tools respond |
| ADO ↔ GitHub link | Azure Boards GitHub app installed | `AB#<id>` in a PR links back to the board — confirm once |

If the `azure-devops` MCP tools are deferred, load them first via ToolSearch (e.g. `select:mcp__azure-devops__wit_get_work_item,mcp__azure-devops__wit_update_work_item,mcp__azure-devops__wit_add_work_item_comment,mcp__azure-devops__wit_link_work_item_to_pull_request`).

**Two machines/filesystems caveat (from repo CLAUDE.md):** the bash tool may run as `root` in a container, not as the operator's user. Do **not** use the bash tool to write files intended for Docker containers. For normal git + code work in `D:\source\github\...` use the standard file/edit tools and git. If a git command needs the operator's credentials/SSH, ask the operator to run it.

---

## 2. What this work is (context)

169 ADO work items remediate an architecture review of **magiq-media** (C#/.NET 8, DDD·CQRS·Event-Sourced, AWS SNS→SQS, DynamoDB/OpenSearch). Six Epics:

- **A** Async integration backbone (34275) — messaging registration + rewire. **A1 (34301) is the root unblocker; A5 (34397) is the deploy re-enable gate.**
- **B** Distributed-systems safety (34276) — consumer contract, saga OCC, projector watermarks.
- **D** Module correctness bugs (34277) — the biggest Epic; per-module bug clusters.
- **E** Contract/validation/spec hygiene (34278).
- **F** Deferred choreography features (34279) — product-gated by spike **INV-4**.
- **G** Observability (34280).

Companion docs in this folder:
- `architecture-review-remediation-pr-plan.md` — full rationale / the "why" behind each item.
- `architecture-review-ado-workitems.md` — ID index (Epic→Feature→Story→Task, plus dependency links). Open any item at `https://dev.azure.com/MAGIQSoftware/Media/_workitems/edit/<id>`.
- `architecture-review-authz-and-outbox-deferred-plan.md` — explicitly deferred scope (authz C6/C8, outbox) — **do not** pull these in without an operator decision.

---

## 3. The core operating loop (one Story = one PR)

**Golden rules (from the plan §0–§4):**
- **`Story/Bug = one PR`.** Epics and Features group work; they are not PRs.
- **The operator creates branches.** You never `git checkout -b` on your own. Names are pre-defined in the plan (§2 naming, §8 full list). Tell the operator the exact **branch name + repo**, wait for "go" / confirmation it exists, then work on it.
- **You do the code AND the spec/ADR changes** on that branch (spec co-locates with code in `D:\source\github\magiq-media\docs\spec\` and `docs\adrs\`).
- **You drive ADO states New → In Progress → Code Review and stop.** QA/release/Done is the operator's team flow (unless the operator tells you to close).

**Per-item sequence:**

1. **Pick** the next ready item — deps met, per wave order (plan §3). Default order: Wave 1 unblock (INV spikes → **A1** → the ★ trivials `34319 34304 34340 34324 34300`), then Wave 2 backbone, etc.
2. **Name the branch + repo** to the operator (plan §8). For cross-repo Stories A2/A4a/A4d = **two branches / two PRs**, one per repo, keyed on Task IDs, both citing the same Story `AB#` (plan §6).
3. **Operator creates the branch** from `develop`. Confirm it exists (`git fetch` + checkout).
4. **ADO:** set the Story + its Task(s) `System.State` → `In Progress` and `System.AssignedTo` → Chase Ramone (`chase.ramone@magiqsoftware.com`). Use `wit_update_work_item`, `op:"Replace"`, path `/fields/System.State` (and `/fields/System.AssignedTo`). **The board rejects `Remove` — use `Replace` with `""` to clear.**
5. **Implement** on the branch: code + spec/ADR. Commit as you go, normal commit messages. Match repo conventions in `CLAUDE.md` (all commands return `Result<T,DomainError>`; every aggregate `ITenanted`, `TenantId` first field immutable; `TenantId` from JWT claim / SNS attribute never payload; DynamoDB PK `TENANT#{TenantId}#{EntityId}`; OCC conditional writes retry ≤3×; UUID v7 typed IDs).
6. **Verify** against the item's **Accept** cell (plan §5) — build + tests green. State the actual result; if tests fail, say so with output.
7. **Open PR** into `develop`, titled `AB#<id> <KEY> — <title>`, body citing the finding IDs it closes. Link PR↔work item (`AB#<id>` in the PR + `wit_link_work_item_to_pull_request` where available).
8. **ADO:** move Story → `Code Review`; add a comment with the PR URL.
9. **Update the tracker:** set the item's **Status** cell in `IMPLEMENTATION-PLAN.md` §5 to `Code Review` (or `Done` when merged), and append one line to §9 **Session log**: `YYYY-MM-DD — what advanced — state changes`.

**Spikes (INV-1/3/4/5, plan §7):** no branch, no PR. Investigate, record findings in the ADO work item **and** in the plan. INV-4 is a **product decision** (build vs defer review saga + signing) that gates A4d and all of Epic F — surface it to the operator, don't decide it yourself.

---

## 4. Start / Continue / End — quick reference

### ▶ START (first session, nothing in progress)
1. Do §0 (read files) and §1 (access check).
2. Wave 1 is the start: run the INV spikes if the operator wants decisions first, then **A1 (34301)** — it unblocks everything async. In parallel the ★ trivials (`34319 34304 34340 34324 34300`) are independent of A1.
3. Name the first branch (`feature/chase/34301-production-messaging-registration`, app repo; may need a platform companion branch if `AddMediaProductionMessaging()` lands in the SDK). Wait for the operator to create it.
4. Run the per-item loop (§3).

### ⏸ CONTINUE (a later session)
1. Do §0. Read the §9 Session log tail + §5 Status columns to find the resume point.
2. If an item is `In Progress`: check out its branch, `git log`/`git status` to see how far it got, resume the loop from where it stopped.
3. If nothing is in progress: pick the next ready item by wave/deps and start the loop.
4. Never assume prior state — verify from git + ADO + the tracker before acting.

### ⏹ END (wrapping a session)
1. For each item touched: PR open + linked, ADO at `Code Review`, tracker Status updated.
2. Append the §9 Session-log line.
3. Leave a one-line "next ready item" note in the session log so the next session starts fast.
4. Summarize to the operator: what advanced, what's blocked, what needs their action (branch creation, INV-4 decision, QA/merge).

---

## 5. Guardrails

- **Don't create branches yourself** — operator does. **Don't merge** — that's the team's flow. **Don't move items past `Code Review`** unless told.
- **Don't pull in deferred scope** (authz C6/C8, outbox) without an operator decision.
- **Don't decide INV-4** (product build-vs-defer) — surface it.
- **Respect dependency gates:** A1 before async work; A5 gates deploy re-enable; B3 waits on INV-1 + INV-5; Epic F waits on INV-4. Deps are in each item's **Deps** cell.
- **Two-sided fixes travel together** — e.g. D-AM3 ↔ D-MI2 (role bind/unbind events), D-MI3 ↔ D-MP2 (conformance), the archive-coordination group D-COL1 + D-FOL2 + D-MI1. Note the pairing in the PR.
- **The tracker is the source of truth.** If this file and `IMPLEMENTATION-PLAN.md` disagree, the tracker wins for state; update this file only if the operating process itself changed.
- **Spec/ADRs live in the app repo**, not this AIOS folder. Edit them under `D:\source\github\magiq-media\docs\`.

---

## 6. Handy index

- Branch names by wave/repo → plan **§8**.
- Cross-repo two-PR Stories → plan **§6**.
- ADO state protocol + field ops → plan **§4**.
- Execution order / waves → plan **§3**.
- Master item tables (Work + Accept per item) → plan **§5**.
- Item ID ↔ title index + board URLs → `architecture-review-ado-workitems.md`.
- Rationale per item → `architecture-review-remediation-pr-plan.md`.

Assignee for everything: **Chase Ramone** (`chase.ramone@magiqsoftware.com`). Board: **Media** (`dev.azure.com/MAGIQSoftware`). Epic tag: `arch-review-remediation`.
