---
name: project-sync
description: Apply pending Hermes captures (updates, ideas, removals, risks, decisions, questions) to an existing project folder. Use when Chase says "sync project [slug]", "apply Hermes updates for [slug]", "process pending [slug] notes".
---

## What this skill does

Reads all pending Hermes data files for a project → groups by type → presents each group
for review → applies confirmed changes to the project folder files.

Nothing is applied without Chase's explicit confirmation per group.

## Procedure

### Step 1: Read all Hermes pending data

From ~/.hermes/data/projects/[slug]/ read:
- updates.json — filter status: "pending"
- removals.json — filter status: "pending"
- ideas.md — all entries
- risks.md — entries not already in projects/[slug]/risks.md
- decisions.md — entries not already in projects/[slug]/decisions/log.md
- questions.md — entries not already in projects/[slug]/notes.md

If nothing pending: "projects/[slug]/ is up to date — no pending Hermes captures."

### Step 2: Present grouped summary

Show one screen:

Pending Hermes captures for [slug]:

UPDATES (N)
  1. [field]: [change summary]

REMOVALS (N) — requires confirmation per item
  1. [target]: [reason]

IDEAS (N)
  1. [title]: [one-line summary]

RISKS (N)
  1. [title] ([impact] impact)

DECISIONS (N)
  1. [title] [ADR candidate? flag if true]

QUESTIONS (N)
  1. [label] [BLOCKING if blocking]

Apply all? Or specify groups: "apply updates", "apply ideas", "skip removals", etc.

### Step 3: Apply confirmed groups

UPDATES:
- Apply each to brief.md and manifest.json.
- Mark status: "applied" with appliedAt timestamp in updates.json.

REMOVALS:
- Show exactly what will be removed and where.
- Confirm per item: "Remove [target] from [scope]? (yes/skip)"
- Only remove on explicit yes.
- Never delete files — only remove content within files.
- Mark status: "applied" or "skipped".

IDEAS:
- Append to notes.md under ## Ideas (from Hermes) section.
- Ask: "Any of these should become ADO items? (list numbers or none)"
- For selected: add to ~/.hermes/data/ado-pending.json.

RISKS:
- Append to risks.md.
- Ask: "Any of these need immediate attention? (list numbers or none)"

DECISIONS:
- Append to decisions/log.md.
- For ADR candidates: "Create formal ADRs for these? (yes/no)"
- If yes: create adrs/ADR-[next-number]-[slug].md using magiq-media ADR format.

QUESTIONS:
- Append to notes.md under ## Open Questions section.
- Ask: "Any already resolved? (list numbers with answers, or none)"
- For resolved: mark with resolution inline.

### Step 4: Report

Sync complete for [slug].

Applied:
  [N] updates to brief.md, manifest.json
  [N] ideas to notes.md
  [N] risks to risks.md
  [N] decisions to decisions/log.md
  [N] questions to notes.md

Skipped:
  [N] removals deferred
  [N] items skipped by choice

## Notes
- Removals always require per-item confirmation. Never auto-apply.
- Do not touch ado-pending.json except for ideas Chase explicitly selects.
- If Hermes MCP unavailable, read data files directly via file read.