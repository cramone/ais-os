---
name: standup-rollup
description: Use when Chase wants a status update, standup summary, sprint rollup, or stakeholder report from Azure DevOps. Triggers on "standup rollup", "status report", "sprint summary", "what shipped this week", "draft a status update", "rollup for [meeting]". Pulls the current ADO iteration and drafts a stakeholder-ready summary in Chase's voice for review.
bike-method-phase: 1  # Phase 1 — Training wheels. Run manually first, review every draft.
three-ms-attribution: |
  Adapted from The Three Ms of AI™ © 2026 Nate Herk.
---

# Standup Rollup

Turns the current Azure DevOps iteration into a **stakeholder-ready status draft in Chase's voice**.

**Autonomy: L2 Drafted.** You draft, Chase edits, Chase sends. Never present output as final. CLAUDE.md rule: no external comms in Chase's voice without showing a draft first.

**KPI:** time-to-status-report (~35 min → <5 min review). Bucket: Less cost.

## When to run

- Weekly — Friday or before a standup / stakeholder meeting
- On-demand — any time Chase asks for a status update or sprint summary

## Inputs

- `scripts/devops_summary.py --all --sprint --json` — current iteration, all assignees, structured JSON (deterministic data pull; 300s cache)
- `references/voice.md` — Chase's register (read before drafting; match it exactly)
- Optional: ask Chase the **audience** (team standup / leadership / customer) and **format** (Teams message / email) if not stated. Default = team standup, Teams message.

## Process

### Step 1 — Pull the data (deterministic, no AI)

Run:

```
python scripts/devops_summary.py --all --sprint --json
```

Parse the JSON. Each item has: `id, title, type, state, assignee, priority, sprint, module, project, tags, url`.

If `total` is 0 → tell Chase "No items in the current iteration" and stop. Don't fabricate.

If the script errors (missing `.env`, network/IP allowlist) → report the exact error. Do NOT guess at status from memory.

### Step 2 — Group (deterministic)

- **By theme** — use `module` / `project` (area path). Map to the Q2 priorities where they fit: magiq-media API, tenant management & auth, user security & policies. Anything else → "Other".
- **Within theme, by state bucket:**
  - ✅ **Shipped / Done** — Done, Closed, Resolved
  - 🔄 **In flight** — Active, In Progress, Code Review, In Review
  - 🚫 **Blocked** — Blocked, plus anything tagged blocked/risk
  - 🆕 **Queued** — New, To Do
- Pull out a **Code Review queue** (state = Code Review) — these are the items needing Chase or the team to act now.

### Step 3 — Draft in Chase's voice (the AI step)

Read `references/voice.md` first. Match the register:
- Direct opener, no preamble, no sign-off pleasantries
- Short declarative sentences, lists over paragraphs
- ✅ / 🚫 for status items
- Precise technical terms, no over-explaining
- Casual-professional

Structure the draft:

```
[One-line opener — what this update covers + sprint name]

✅ Shipped
- [theme]: [plain-language outcome, not the raw ticket title] (#id)

🔄 In flight
- [theme]: [what's moving, who's on it if leadership audience] (#id)

🚫 Blocked / risks
- [theme]: [what's stuck + why if known] (#id)

[Optional: Code review queue — N items waiting]
```

Drafting rules:
- **Translate, don't transcribe.** Turn "Implement IUserPolicy resolver" into "User policy resolution — in progress". Stakeholders want outcomes, not ticket titles.
- **Surface signal, drop noise.** Don't list all 30 items. Lead with blockers and shipped work. Collapse routine tasks into a count ("+6 routine tasks progressing").
- **Audience-adjust:** leadership → themes + risks, fewer IDs, name owners. Team standup → more detail, IDs kept. Customer → outcomes only, no internal IDs or names.
- **Don't invent status.** If the data doesn't say it's blocked, don't say it's blocked. Flag uncertainty plainly ("not sure why #123 stalled — worth a check").

### Step 4 — Hand off for review

Present the draft and say plainly it's a draft for review. Offer:
- Edit tone/length/detail
- Re-cut for a different audience
- Once Chase approves, he sends it (or asks to push via Hermes/Teams)

Never auto-send. L2 means human edits before send.

## Boring-is-Beautiful note

The data pull and grouping are deterministic — the only AI is the prose draft in Step 3. Don't add reasoning steps the task doesn't need. Ship the draft, expand from real use.

---

*Adapted from The Three Ms of AI™ © 2026 Nate Herk. All rights reserved.*
