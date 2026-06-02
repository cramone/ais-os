---
name: project-review
description: Show a full status summary of a project — open questions, risks, pending ideas, decisions, and unsynced Hermes captures. Use when Chase says "review project [slug]", "status of [slug]", "what is pending for [slug]", "where are we with [slug]". Read-only — nothing is written.
---

## What this skill does

Reads both the AIS-OS project folder and any pending Hermes data for a project →
produces a single consolidated status screen. Strictly read-only.

## Procedure

### Step 1: Read project folder

From projects/[slug]/:
- MEMORY.md — current status line
- risks.md — count unresolved risks, flag any high-impact
- decisions/log.md — count decisions; flag ADR candidates not yet formalised
- notes.md — count open questions; count unaddressed ideas

### Step 2: Read Hermes pending data

From ~/.hermes/data/projects/[slug]/:
- updates.json — count status: "pending"
- removals.json — count status: "pending"
- ideas.md — count total entries
- risks.md — count entries not yet in project folder
- decisions.md — count entries not yet in project folder
- questions.md — count entries not yet in project folder

### Step 3: Output status screen

--- [displayName] — Project Review ---
Status: [status from MEMORY.md]
Priority: [priority] | ADO Board: [adoBoard]

IN PROJECT FOLDER
  Open questions:   [N]  [BLOCKING: N if any blocking]
  Unresolved risks: [N]  [HIGH: N if any high-impact]
  Decisions logged: [N]  [ADR candidates pending: N if any]
  Ideas noted:      [N]

PENDING IN HERMES (not yet synced)
  Updates:          [N]
  Removals:         [N]
  New ideas:        [N]
  New risks:        [N]
  New decisions:    [N]
  New questions:    [N]

[If all Hermes counts 0: "Hermes fully synced."]
[If any Hermes counts > 0: "Run sync project [slug] to apply pending captures."]

SPEC STATUS
  [If spec/ is empty: "Spec not started."]
  [If spec/ has files: list files with last modified date]

NEXT ACTION
  [One-line recommendation]
---

## Notes
- Never write anything. Strictly read-only.
- If Hermes MCP unavailable, note it and show AIS-OS folder data only.
- If project folder does not exist: "No project folder found for [slug]. Run scaffold project [slug] first."