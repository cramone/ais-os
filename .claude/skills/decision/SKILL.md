---
name: decision
description: Use when Chase says "log this decision", "save this decision", "remember this decision", "log a decision", "/decision", or makes a notable architectural, technical, or strategic call and wants it captured. Formats and appends an entry to decisions/log.md immediately.
---

## What this skill does

Captures a decision from the current conversation and appends a formatted entry to
`decisions/log.md`. Append-only — never edits or removes existing entries.

Eliminates the friction between making a decision and persisting it. One trigger, done.

---

## When to trigger proactively

Don't wait to be asked. If Chase makes a call that fits any of these, offer:
"Want me to log that decision?"

- Chooses one architecture pattern over another
- Defers or descopes a feature with a reason
- Decides on a tool, library, or integration approach
- Sets a convention that will apply across the codebase
- Resolves a tradeoff after weighing alternatives
- Changes direction on something previously decided

If it's a throwaway comment, skip it. If it's something future-Chase would want to know the
*why* behind — offer to log it.

---

## Execution

### Step 1 — Extract decision details from conversation

Pull from what's already been said. Only ask Chase for what's genuinely missing.

Required fields:
- **Title** — short phrase, e.g. "Use UUIDv7 for aggregate IDs"
- **Decision** — what was decided, one sentence
- **Why** — the reasoning and constraints
- **Alternatives considered** — what else was on the table (can be "None considered" if not discussed)
- **Owner** — default to "Chase Ramone" unless another name was mentioned

Optional:
- **Revisit when** — include if there's a clear condition that would change the decision

### Step 2 — Confirm before writing

Show Chase the formatted entry and ask: "Log this?" 

Do not append without confirmation.

### Step 3 — Append to decisions/log.md

Once confirmed, append to `decisions/log.md`:

```
## {YYYY-MM-DD} — {Title}

**Decision:** {what was decided}

**Why:** {reasoning and constraints}

**Alternatives considered:** {alternatives}

**Owner:** {owner}
```

Include `**Revisit when:**` line only if applicable.

Use today's date. Append after the last entry, preceded by `---`.

Confirm to Chase: "Logged. decisions/log.md updated."

---

## Format rules

- Title: title case, no punctuation at end
- Decision: single declarative sentence
- Why: 1-3 sentences max — capture the *why*, not a full essay
- Alternatives: comma-separated or short bullets if >2
- Keep the whole entry under 10 lines
- Never modify existing entries

---

## Examples

### Architecture decision
```
## 2026-05-24 — DynamoDB Conditional Writes for Optimistic Concurrency

**Decision:** Use DynamoDB conditional writes (`attribute_not_exists(AggregateVersion)`) for
optimistic concurrency, retrying up to 3× with exponential backoff.

**Why:** Native to DynamoDB, no additional infrastructure, deterministic failure mode.
Retry cap prevents infinite loops on genuine conflicts.

**Alternatives considered:** Pessimistic locking (too slow for Lambda cold-start latency),
DynamoDB transactions (overkill for single-aggregate writes).

**Owner:** Chase Ramone
```

### Deferral decision
```
## 2026-05-24 — DocumentSigningSaga Deferred to Post-Q2

**Decision:** Defer DocumentSigningSaga implementation until after Q2 API completion.

**Why:** DocumentSigning module is not on the Q2 critical path. Building the saga now would
block higher-priority write-model completions.

**Alternatives considered:** Partial implementation — rejected, leaves system in inconsistent
state that's harder to clean up than a clean deferral.

**Owner:** Chase Ramone

**Revisit when:** magiq-media API is feature-complete and Q2 priorities are met.
```

### Convention decision
```
## 2026-05-24 — TenantId Never Derived from OwnerId

**Decision:** TenantId is always sourced from JWT tenant_id claim or SNS message attribute —
never derived from OwnerId or any other field.

**Why:** OwnerId is mutable (ownership can transfer); TenantId must be stable for DynamoDB
key consistency. Deriving one from the other would introduce a silent invariant violation.

**Alternatives considered:** None — this is a hard architectural constraint.

**Owner:** Chase Ramone
```

---

## Notes

- Date is always today's date — use `date +%Y-%m-%d` or equivalent to get it.
- If Chase gives a vague trigger ("log that"), infer the decision from recent conversation context.
- If context is too ambiguous to construct a clean entry, ask one clarifying question: "What was
  the decision?" Then proceed.
- For architecture decisions that warrant a full ADR (significant, long-lived, cross-cutting),
  suggest: "This one's ADR-worthy — want me to create a full ADR in projects/magiq-media/adrs/
  as well?"
