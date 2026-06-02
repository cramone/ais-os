# EXPANSIONS — what to add as you grow

The system starts lean on purpose.

You are building a working system, not a folder structure.

Add only when needed.

---

## What ships in the base system (do not remove)

| Folder / file | Purpose |
|---|---|
| `context/` | About you, your role, constraints, priorities |
| `references/` | Frameworks, APIs, SOPs |
| `decisions/log.md` | Source of truth for decisions |
| `archives/` | Old or unused content |
| `connections.md` | Systems you interact with |
| `.claude/skills/` | `/onboard`, `/audit`, `/level-up` |
| `aios-intake.md` | Input for `/onboard` |
| `CLAUDE.md` | Operating manual |

---

## What to add as you grow

Only add when the need is real.

---

### `projects/`

**Add when:**
- You have 2+ structured initiatives

**Why:**
- Keeps complex work isolated from general context

#### Active projects

| Slug | Name | Priority | Status |
|------|------|----------|--------|
| magiq-media | MAGIQ Media | High | Active |
| document-lifecycle-cleaner | Document Lifecycle Cleaner | — | Active |
| magiq-auth | MAGIQ Auth | High | Draft |

---

### `templates/`

**Add when:**
- You repeat the same prompts or documents

**Why:**
- Reduces drift and rework

---

### `references/sops/`

**Add when:**
- A process is repeated or handed to someone else

**Why:**
- Enables consistency and delegation

---

### `references/{tool}-api.md`

**Add when:**
- You integrate a new tool or API

**Why:**
- Capture once, reuse forever

---

### `references/adrs/`

**Add when:**
- Any significant architecture or technology decision is made

**Why:**
- Prevents relitigating decisions; gives new team members context on why things are built the way they are

---

### `team/`

**Add when:**
- Team grows beyond 3 people or roles become specialised

**Why:**
- Skills matrix, roster, and capacity visibility reduce planning blind spots

---

### `reviews/`

**Add when:**
- Code review patterns repeat or standards need enforcing

**Why:**
- PR checklists and review templates reduce inconsistency and rework

---

### `tech-debt/`

**Add when:**
- Tech debt competes with feature work for prioritisation

**Why:**
- Makes debt visible and trackable alongside active work

---

### `roadmap/`

**Add when:**
- Planning spans multiple sprints or involves stakeholder alignment

**Why:**
- Single source of truth for what's coming and why

---

### `scripts/`

**Add when:**
- You need automation not covered by integrations

**Why:**
- Scripts are often the fastest second step

---

### `.claude/agents/`

**Add when:**
- You need repeatable multi-step workflows

**Why:**
- Keeps main context clean and efficient

---

### `hermes/` (Hermes background agent)

**Add when:**
- Hermes is deployed, MCP connection verified, and skills are in active use

**Why:**
- Documents the Hermes integration pattern and skill split between Hermes and Claude Code
- Reference for what Hermes captures (notes, digests, cron) vs what Claude Code executes (ADO writes, spec work)
- Skills live at `C:\Users\chase\.hermes\skills\` — not in AIS-OS, but document the pattern here

**Integration points:**
- MCP connection: `.claude/settings.json` → `docker exec -i hermes /opt/hermes/.venv/bin/hermes mcp serve`
- Data files: `C:\Users\chase\.hermes\data\ado-pending.json`, `flagged-comms.json`, `projects/[slug]/`
- Execution skills: `.claude/skills/ado-flush/`, `project-scaffold/`, `project-sync/`, `project-review/`
- Constraint: Hermes never calls ADO API directly — org IP allowlist blocks cloud-origin requests
- Project capture flow: Telegram → Hermes skill (`project-create` etc.) → `~/.hermes/data/projects/[slug]/` → Claude Code `scaffold`/`sync`/`review`

---

### Sub-OS (e.g. `youtube-os/`)

**Add when:**
- A domain has its own workflows and data

**Why:**
- Isolates complexity

---

### Work management (`work/`)

**Add when:**
- You are juggling multiple concurrent streams

**Why:**
- Provides clarity across active work

---

### Execution systems (`execution/`)

**Add when:**
- You repeat the same types of tasks

**Why:**
- Standardises how work gets done

---

### Knowledge base (`knowledge/`)

**Add when:**
- You reuse the same patterns or system knowledge

**Why:**
- Prevents rethinking

---

### Communication (`communication/`)

**Add when:**
- You repeatedly write similar updates or proposals

**Why:**
- Speeds up output

---

### Improvement (`improvement/`)

**Add when:**
- You actively reflect and optimise

**Why:**
- Captures learning and progress

---

## Suggested cadences

- `decisions/log.md` — whenever a decision is made
- `references/adrs/` — whenever an architecture decision is made
- `archives/` — quarterly cleanup
- `references/sops/` — when a process repeats
- `connections.md` — when a new system is added
- `CLAUDE.md` — quarterly review
- `team/` — when team roster or roles change
- Sprint review — after each sprint, update `roadmap/` and log decisions
- 1:1 prep — before each session, pull from `team/` and `decisions/log.md`

---

## What NOT to add

Avoid these patterns:

- Dumping raw data into `references/`
- Creating deep folder hierarchies
- Adding `notes/`, `misc/`, `tmp/`, `inbox/`
- Pre-creating unused folders
- Duplicating decision sources
- Forking the operating manual

---

## When to add structure

Ask:

1. Is this a new concept?
2. Will I use this 3+ times soon?
3. Will it reduce friction or repeated thinking?

If yes to at least two → add it

If not → wait

---

## Guiding principle

A good system feels:

- Easy to navigate
- Hard to misuse
- Lightweight

If it starts feeling heavy, you added too much.

---

## Final rule

Do not organise for the sake of organisation.

Only organise what earns its place.
