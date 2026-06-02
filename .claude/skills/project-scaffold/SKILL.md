---
name: project-scaffold
description: Scaffold a new project folder in AIS-OS from a Hermes-captured brief. Use when Chase says "scaffold project [slug]", "set up [slug]", "create the folder for [slug]", or after a Hermes project-create capture.
---

## What this skill does

Reads Hermes data for a captured project via Hermes MCP (or direct file read fallback) →
creates the full project folder structure in projects/[slug]/ aligned with the magiq-media
and document-lifecycle-cleaner conventions → registers in EXPANSIONS.md.

## Procedure

### Step 1: Read Hermes data

Read via Hermes MCP or file fallback:
- ~/.hermes/data/projects/[slug]/manifest.json
- ~/.hermes/data/projects/[slug]/brief.md

If neither exists:
"No Hermes data found for [slug]. Capture it first with new project [name] in Telegram."

### Step 2: Check for existing folder

If projects/[slug]/ already exists:
"projects/[slug]/ already exists. Run sync project [slug] to apply pending updates instead."
Stop.

### Step 3: Scaffold the folder

Create projects/[slug]/ with these files:

#### projects/[slug]/brief.md
Copy from Hermes brief.md. Add header line:
_Scaffolded: [ISO timestamp] | Source: Hermes capture_

#### projects/[slug]/CLAUDE.md
---
# [displayName]

## Project Overview
[description from manifest]

**Current status:** Draft — scaffolded from Hermes capture. Spec not yet started.

## Stack
[stack from manifest]

## Modules
[modules — one per line]

## Integrations
[integrations from manifest]

## ADO Board
[adoBoard from manifest]

## Priority
[priority from manifest]

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints |
| notes.md | Open question resolutions and session notes |
| risks.md | Risk register |
| decisions/log.md | Architecture and design decisions (append-only) |
| spec/ | Spec files |

## Decisions

All architecture and design decisions go in decisions/log.md.

---

## Memory System

This folder contains MEMORY.md — your external memory for this project.

At the start of every session: Read MEMORY.md before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when Chase explicitly asks using phrases like
"remember this", "make a note", "log this", "save this". Write immediately and confirm.

All memories are persistent until Chase explicitly asks to remove or change them.

Flag contradictions — never silently overwrite.
---

#### projects/[slug]/MEMORY.md
---
# Memory — [slug]
_Last updated: [ISO date]_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Status**: Draft — scaffolded [date], spec not yet started
- **Priority**: [priority]
- **ADO Board**: [adoBoard]
---

#### projects/[slug]/notes.md
---
# Notes — [displayName]

_Open questions, session notes, and resolutions._

---
---

#### projects/[slug]/risks.md
---
# Risks — [displayName]

_Imported from Hermes captures. Add new risks via risk for [slug] in Telegram or directly here._

---
[If ~/.hermes/data/projects/[slug]/risks.md has content, import it verbatim]
---

#### projects/[slug]/decisions/log.md
---
# Decision Log — [displayName]

_Append-only. All architecture and design decisions recorded here._

---
[If ~/.hermes/data/projects/[slug]/decisions.md has content, import it verbatim]
---

#### projects/[slug]/spec/
Create empty directory only. Do not create files inside.

### Step 4: Register in EXPANSIONS.md

Append under the projects/ section:

#### projects/[slug]/
**[displayName]**
[description — one sentence]
Priority: [priority] | ADO Board: [adoBoard] | Status: Draft

### Step 5: Report

Created files:
  projects/[slug]/brief.md
  projects/[slug]/CLAUDE.md
  projects/[slug]/MEMORY.md
  projects/[slug]/notes.md
  projects/[slug]/risks.md
  projects/[slug]/decisions/log.md
  projects/[slug]/spec/

[If Hermes had risks: N risks imported]
[If Hermes had decisions: N decisions imported]
[If Hermes had ideas/questions: N items pending — run sync project [slug]]

Registered in EXPANSIONS.md.

## Notes
- adrs/ directory: only create if the project is clearly architectural (has modules, complex integrations).
- Never create content in spec/ — that is deliberate spec work, not scaffolding.
- If Hermes MCP is unavailable, read ~/.hermes/data/projects/[slug]/ directly via file read.