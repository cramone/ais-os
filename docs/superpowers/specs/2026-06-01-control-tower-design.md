# AIS-OS Control Tower — Design Spec

**Date:** 2026-06-01  
**Status:** Approved for implementation  
**Stack:** Python FastAPI + Vanilla JS (single HTML file)  
**Refresh:** Auto-polling every 30s  

---

## Overview

A locally-hosted browser dashboard that surfaces everything in AIS-OS in one place. Replaces context-switching between ADO, Hermes, project files, and Claude Code for status and triage. Designed for a team lead who is also an active developer.

**Single command to run:**
```bash
python tower/server.py
# opens http://localhost:8765
```

---

## Architecture

```
tower/
  server.py          # FastAPI app — all API routes + static file serving
  data/
    interrupts.json  # Interrupt storage (local-first)
  static/
    index.html       # Single-page app (all JS/CSS inline)
```

**No build step. No npm. No separate frontend server.**

The backend reads from:
- `projects/*/MEMORY.md` — project status/priority
- `C:\Users\chase\.hermes\data\ado-pending.json` — Hermes ADO captures
- `C:\Users\chase\.hermes\data\projects\*/` — Hermes project captures
- `C:\Users\chase\.hermes\data\adhoc-notes.md` — adhoc notes
- `decisions/log.md` — decision history
- ADO via existing `devops_summary.py` script — live sprint data
- `tower/data/interrupts.json` — interrupt list

---

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/projects` | All project MEMORY.md summaries |
| GET | `/api/ado/sprint` | Live ADO data via devops_summary.py |
| GET | `/api/hermes/inbox` | ado-pending.json pending items |
| GET | `/api/hermes/sync` | Per-project pending captures |
| GET | `/api/adhoc-notes` | Parsed adhoc-notes.md entries |
| GET | `/api/decisions` | Last 10 entries from decisions/log.md |
| GET | `/api/interrupts` | All interrupts from interrupts.json |
| POST | `/api/interrupts` | Create new interrupt |
| PATCH | `/api/interrupts/{id}` | Update interrupt (status, priority, due date) |
| DELETE | `/api/interrupts/{id}` | Delete interrupt |
| POST | `/api/interrupts/{id}/push-ado` | Push interrupt to ADO as Task |
| POST | `/api/interrupts/{id}/activity` | Append comment to activity feed |
| POST | `/api/interrupts/{id}/email-draft` | Generate email draft via Claude API |
| GET | `/api/health` | Connection status for all data sources |

All routes return JSON. Errors return `{"error": "...", "source": "..."}` — failed sources degrade gracefully (panel shows stale/error state, others keep loading).

---

## Frontend Layout

### Top Bar
- App name + subtitle
- Status pills: Hermes live · ADO connected · N pending flush · N blocked (auto-derived from API health + data counts)
- Last-refreshed timer + manual Refresh button
- Current date/time

### Left Sidebar
Sections: My Work · Interrupts · Projects · Inbox · Team · History · Reference

Each section has nav items with live badge counts pulled from panel data.

### Main Content (top to bottom)

**1. Focus Strip**  
Current in-progress ADO item. Source: items with state `Active`/`In Progress` assigned to Chase, sorted by last-updated. Shows: title, project·module·state, days active. Actions: Skip (moves to next active), Mark done (updates ADO state), Open in ADO.

Also shows interrupt impact inline: "N interrupts competing with sprint focus" if overdue/due-today interrupts exist.

**2. Blocked Banner**  
Shown only when blocked items exist. Red-tinted. Lists: who is blocked, reason (ADO item title), days blocked. Source: ADO items with state `Blocked`.

**3. Standup Prep Strip**  
Three columns: Yesterday / Today / Blockers. Auto-generated:
- Yesterday: ADO items changed to Done/Closed in last 24h
- Today: current In Progress + In Review items (top 3)
- Blockers: Blocked ADO items + overdue interrupts
"Copy to clipboard" button formats as plain text for Teams paste.

**4. Projects Row**  
Cards per project from MEMORY.md. Each card shows: name, priority chip, status text, sprint health bar (% done + days left — from ADO epic/sprint data), meta chips (item count, in-review count, blocked count, pending flush count).

Click card → drill-down panel expands below with full project detail.

**5. Main Panel Grid (3 columns)**

*ADO Sprint panel*  
Tabbed: My Items / In Review / Team. Each row: state dot + title + module·type·state. In Review tab adds review age badge (green < 2d, amber 2–5d, red > 5d). Blocked items shown in red with days blocked.

*Hermes Inbox panel*  
Pending items from ado-pending.json. Each row: type icon + title + project·module·type. "Flush all" action button triggers `flush pending notes` workflow (opens Claude Code instruction). Badge count synced to sidebar.

*Interrupts panel (compact)*  
Shows overdue + due-today items highlighted. "View all" links to full Interrupts view. Quick-capture input inline at bottom of panel.

**6. Team Workload Row**  
One card per team member (Chase, Estelle, Akshay). Each shows: name, role, stat chips (active/review/blocked counts), current WIP item. Source: ADO items grouped by assignee.

**7. Decisions + Hermes Sync Row (2 columns)**  
Recent decisions from decisions/log.md (date + text + project tag).  
Hermes sync status per project (last synced + pending capture count).

**8. Cheat Sheet (collapsible)**  
4-column grid. Sections: Hermes Triggers · Claude Code Commands · AIS-OS Workflows · Keyboard Shortcuts. Collapsed by default after first visit (preference stored in localStorage).

---

## Interrupts Feature

### Data Model

```json
{
  "id": "uuid-v4",
  "title": "Fix document export failing for NATA client",
  "source": "Support",
  "dueDate": "2026-06-01",
  "priority": "urgent",
  "status": "new",
  "tags": ["blocked", "waiting-for-feedback"],
  "adoItemId": null,
  "capturedAt": "2026-05-29T08:22:00Z",
  "updatedAt": "2026-05-29T08:22:00Z",
  "activity": [
    {
      "type": "comment",
      "author": "Chase",
      "text": "Root cause is null reference in PDF renderer...",
      "timestamp": "2026-05-29T09:15:00Z"
    },
    {
      "type": "event",
      "text": "Added tag: blocked",
      "timestamp": "2026-05-29T09:18:00Z"
    }
  ]
}
```

**Sources:** Support · Finance · Product · Executive · Internal  
**Priority:** urgent · normal · low (manual or auto-derived: Executive + due today = urgent)  
**Status:** new · in-progress · deferred · done  
**Tags (built-in):** blocked · waiting-for-feedback · requested-review · needs-more-info · complete  
Custom tags supported — any string value.

### Activity Feed

Each interrupt has an append-only `activity` array. Two entry types:

**Comment** — free-text note added by Chase. Author, text, timestamp.  
**Event** — system-generated on any state change: tag added/removed, status changed, ADO pushed, due date set. Text auto-generated (e.g. "Tag 'blocked' removed · added 'waiting-for-feedback'").

Activity renders as an interleaved chronological feed in the drill-down panel.

### Drill-Down Panel

Expands below the interrupt list row on click. Two-column layout:

**Left — Tags + Activity:**
- Tag chips (clickable toggles). Built-in set + "+ add tag" for custom. Tag changes append an event to activity.
- Full activity feed (comments + events, newest at bottom)
- Add comment textarea + Save button

**Right — Email Draft:**
See Email Draft section below.

### Full Interrupts View

Accessible via sidebar. Contains:
- Quick capture bar (title · source dropdown · optional due date · Capture button)
- Triage counts: Overdue · Due Today · Open · Done this week
- Tabbed list: Open / In Progress / Done / All
- Filter chips: by source · has due date · overdue · by tag
- Each row: priority dot · title · source tag · active tags · age · due chip · status tag · → ADO · ✓ Done

### Email Draft

Generated on demand in the drill-down right panel. Uses interrupt title, source, comments, and tags as context to produce a pre-written email.

**Templates (user selects one):**
- ✅ Job complete — notifies requester task is done
- ⏳ Waiting on you — chases requester for action/response
- 💬 Need more info — requests clarification before proceeding
- 🔄 Status update — mid-task progress summary

**Tone selector:** Formal · Friendly · Brief (changes register of generated text)

**Recipient:** Auto-inferred from most recent comment (looks for email address pattern). Editable.

**Generation:** Server-side via `POST /api/interrupts/{id}/email-draft` with `{ template, tone }`. Backend constructs prompt from activity feed + interrupt metadata, calls Claude API (Haiku), returns `{ to, subject, body }`.

**Actions:**
- Copy text — copies body to clipboard
- Edit draft — makes body textarea editable inline
- Open in Outlook — opens `mailto:{to}?subject={subject}&body={body}` in system mail client
- Regenerate — re-calls API with same template/tone

Draft is not stored — regenerated each time. User edits are local only.

### ADO Push

`POST /api/interrupts/{id}/push-ado` creates ADO Task:
- Title: `[Interrupt] {title}`
- Description: `Source: {source}. Captured: {capturedAt}.\n\nNotes:\n{comments joined}`
- Area path: General
- Due date if set

On success: stores `adoItemId`, button changes to "View in ADO".

---

## Auto-Refresh

Frontend polls `GET /api/health` every 10s (lightweight). Full data refresh every 30s via `Promise.all` across all API endpoints. Each panel updates independently — a slow ADO call doesn't block Hermes panel rendering.

User can force-refresh with Ctrl+R or the Refresh button.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+R | Force refresh all panels |
| Ctrl+K | Focus quick-capture bar |
| Esc | Close drill-down panel |
| F | Toggle Focus Mode (hide everything except Focus Strip + ADO) |
| S | Jump to Standup Prep |
| I | Jump to Interrupts |

---

## Drill-Down

Click any project card, ADO item, or interrupt row → a full-width detail panel expands below the triggering section. Esc or clicking elsewhere closes it.

Project drill-down shows: full MEMORY.md content, all ADO items for that project (tabbed by state), pending Hermes captures, recent decisions tagged to the project.

ADO item drill-down shows: title, description, acceptance criteria, state history (if available), linked items.

Interrupt drill-down shows: full details + notes field (editable inline) + audit trail of status changes.

---

## Startup & Config

`tower/server.py` reads paths from environment or falls back to defaults:

```python
AIOS_ROOT = os.getenv("AIOS_ROOT", r"C:\Users\chase\OneDrive\Magiq\AIS-OS")
HERMES_DATA = os.getenv("HERMES_DATA", r"C:\Users\chase\.hermes\data")
ADO_SCRIPT = os.path.join(AIOS_ROOT, "references", "devops_summary.py")
INTERRUPTS_FILE = os.path.join(AIOS_ROOT, "tower", "data", "interrupts.json")
PORT = int(os.getenv("TOWER_PORT", "8765"))
```

On start: opens `http://localhost:8765` in default browser automatically.

---

## Out of Scope (v1)

- Authentication (local-only, no auth needed)
- Mobile layout
- Push notifications
- Multi-user / team-shared view
- Historical sprint velocity charts
- Hermes direct write from dashboard (read-only for Hermes data in v1)
