---
name: agenda-generator
description: Generate meeting agendas per project and meeting type. Triggered by "generate agenda", "create agenda", "agenda for [project]", "meeting agenda", "[meeting type] agenda for [project]". Also handles adding/removing participants from meeting configs.
---

## Purpose

Generate formatted meeting agendas from per-project config. Save to project agendas folder. Support participant management. Detect unknown people and capture them to the team registry.

## Project Slugs

| Slug | Aliases |
|---|---|
| `magiq-media` | "media", "magiq media" |
| `magiq-auth` | "auth", "magiq auth" |
| `document-lifecycle-cleaner` | "doc cleaner", "lifecycle cleaner", "dlc" |

## Config Locations

- Meeting config: `projects/{slug}/meetings/config.json`
- Team registry: `context/team-members.json`

## Agenda Output Location

`projects/{slug}/meetings/agendas/YYYY-MM-DD-{meeting-id}.md`

---

## Step 1 — Resolve project

Detect slug from request. If ambiguous or missing → ask: "Which project? (magiq-media / magiq-auth / document-lifecycle-cleaner)"

## Step 2 — Resolve meeting type

Read `config.json`. List available meeting `id` values. If request names one clearly → use it. If ambiguous → ask: "Which meeting type? [{id list}]"

## Step 3 — Resolve participants

Read `context/team-members.json`. For each email in the meeting's `participants` array, match against registry by email.

**Unknown participant detection:**
If any participant email OR any name mentioned in the request does NOT exist in `context/team-members.json`:
1. Pause and ask Chase:
   > "I don't recognise **{name/email}**. Can you tell me:
   > - Full name
   > - Email (if not given)
   > - Department
   > - Role"
2. On reply → append new entry to `context/team-members.json`
3. Continue generating agenda

## Step 4 — Generate agenda

Use this exact template:

```markdown
# {project display name} — {topic}

**Date:** {today YYYY-MM-DD}
**Duration:** {duration_min} min
**Participants:** {participant names + roles, e.g. "Chase Ramone (Engineering Lead), ..."}

---

{for each section, numbered:}
## {n}. {title} ({minutes} min)

-
-

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

## Step 5 — Save

Write generated agenda to `projects/{slug}/meetings/agendas/YYYY-MM-DD-{id}.md`.

Confirm: `Agenda saved → projects/{slug}/meetings/agendas/{filename}`

Then print the full agenda to the conversation.

---

## Participant Management

### Add participant

Trigger: "add [name/email] to [meeting type] for [project]"

1. Check `context/team-members.json` for match by name or email
2. **If not found** → ask:
   > "I don't have **{name}** in the team registry. Can you tell me:
   > - Full name
   > - Email
   > - Department
   > - Role"
   Then append to registry before continuing.
3. Read `projects/{slug}/meetings/config.json`
4. Find matching meeting by `id`
5. Append email to `participants` array (no duplicates)
6. Write updated config
7. Confirm: `Added {name} ({role}) to {meeting-id} — {slug}`

### Remove participant

Trigger: "remove [name/email] from [meeting type] for [project]"

1. Read config
2. Remove matching entry from `participants`
3. Write updated config
4. Confirm: `Removed {name} from {meeting-id} — {slug}`

### List participants

Trigger: "who's in [meeting type] for [project]" / "show participants"

1. Read config + team registry
2. Print name, role, email for each participant in that meeting

---

## Rules

- Never skip the unknown-person prompt — always capture new people to the registry
- Default email domain: `@magiqsoftware.com` if domain omitted
- Never ask for confirmation before generating — generate then confirm
- Always save before printing
- Date = today UTC (use currentDate from context if available)
- If config.json missing for project → say "No meetings configured for {slug}."
- Participant display in agenda uses Name (Role), not raw email
