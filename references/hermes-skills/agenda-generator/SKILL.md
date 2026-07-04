---
name: agenda-generator
description: Generate meeting agendas per project and meeting type. Save to project agendas folder. Manage participants. Detect and register unknown team members.
triggers:
  - "generate agenda"
  - "create agenda"
  - "agenda for"
  - "meeting agenda"
  - "standup agenda"
  - "sprint review agenda"
  - "architecture agenda"
  - "security review agenda"
  - "requirements agenda"
  - "add * to * meeting"
  - "remove * from * meeting"
  - "who's in * meeting"
  - "show participants"
---

## Purpose

Generate formatted meeting agendas from per-project config files in the AIS-OS workspace. Capture unknown team members to the central registry before proceeding.

## Workspace Root

`/mnt/shared/claudia/magiq/`

## Project Slugs

| Slug | Aliases |
|---|---|
| `magiq-media` | "media", "magiq media" |
| `magiq-auth` | "auth", "magiq auth" |
| `document-lifecycle-cleaner` | "doc cleaner", "lifecycle cleaner", "dlc" |

## Config Locations

- Meeting config: `/mnt/shared/claudia/magiq/projects/{slug}/meetings/config.json`
- Team registry: `/mnt/shared/claudia/magiq/context/team-members.json`
- Agenda output: `/mnt/shared/claudia/magiq/projects/{slug}/meetings/agendas/YYYY-MM-DD-{meeting-id}.md`

---

## Generate Agenda Flow

### Step 1 — Resolve project

Detect slug from message. If missing → reply: "Which project? (magiq-media / magiq-auth / document-lifecycle-cleaner)"

### Step 2 — Resolve meeting type

Read `config.json`. If meeting type not specified → reply: "Which meeting? [{id list}]"

### Step 3 — Resolve participants

Read `context/team-members.json`.

**If any participant email in the meeting config OR any name in the request is NOT in the registry:**
Reply:
> "I don't recognise **{name/email}**. Tell me:
> - Full name
> - Email
> - Department
> - Role"

On receipt → append to `/mnt/shared/claudia/magiq/context/team-members.json` then continue.

### Step 4 — Generate agenda

Template:

```markdown
# {project display name} — {topic}

**Date:** {YYYY-MM-DD}
**Duration:** {duration_min} min
**Participants:** {Name (Role), Name (Role), ...}

---

## 1. {section title} ({minutes} min)

-
-

## 2. {section title} ({minutes} min)

-
-

[... continue for all sections]

---

## Decisions

-

## Action Items

| Action | Owner | Due |
|--------|-------|-----|
|        |       |     |

## Next Meeting

**Date:**
**Topic:**
```

### Step 5 — Save and reply

Write to `/mnt/shared/claudia/magiq/projects/{slug}/meetings/agendas/YYYY-MM-DD-{id}.md`

Reply with:
```
✅ Agenda saved → projects/{slug}/meetings/agendas/{filename}

{full agenda text}
```

---

## Participant Management

### Add participant

Trigger: "add [name] to [meeting type] for [project]"

1. Check registry — if not found, ask for name/email/department/role → append to registry
2. Read meeting config → append email to `participants` (no duplicates) → write config
3. Reply: `Added {name} ({role}) to {meeting-id} — {slug}`

### Remove participant

Trigger: "remove [name] from [meeting type] for [project]"

1. Read config → remove email → write config
2. Reply: `Removed {name} from {meeting-id} — {slug}`

### List participants

Trigger: "who's in [meeting type] for [project]"

Read config + registry → reply with name, role, email per participant.

---

## Rules

- Always check registry before adding anyone to an agenda or meeting
- Never skip the unknown-person prompt
- Default email domain: `@magiqsoftware.com` if omitted
- Date = today's date (UTC)
- Participant display in agenda = Name (Role), not raw email
- Never confirm before generating — generate then confirm
