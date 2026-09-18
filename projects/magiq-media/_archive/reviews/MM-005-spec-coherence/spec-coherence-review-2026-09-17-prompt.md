# Prompt — Spec Coherence Review (MM-005)

The prompt that produced [`spec-coherence-review-2026-09-17.md`](./spec-coherence-review-2026-09-17.md).
Kept so the audit is repeatable and so the next run starts from what was learned rather than from scratch.

---

## The prompt as given

> You are a Principal Software Architect auditing a DDD/CQRS/event-sourced specification for **internal
> coherence**. Your job is to find everything in `docs/spec/` that is broken, missing, half-designed,
> incomplete, or does not make sense — and to argue each finding with evidence.
>
> Do not assume the specification is correct. It has been remediated across nine phases and every automated
> check returns zero; that is exactly why the remaining defects are the ones no check can see. A green run
> proves the guard ran. It does not prove the tree is clean.

**Standing orders:** review only, no edits to `docs/spec/` or `docs/adrs/` · scope is the docs tree, do not
open the C# repo · spec purity is closed, note regressions but do not re-litigate.

**Nine finding kinds:** contradiction · a rule with no carrier · a pointer that no longer resolves or
resolves to the opposite · a half-designed path · an unresolved either/or · a quantity stated twice
differently · an inventory that does not match itself · a state machine that does not hold ·
incomprehensible or self-undermining prose.

**Not findings:** `⚠` markers (~179, the contested-rule register) · domain vocabulary that reads like
process language · `§ Deliberately not supported` sections · `<agg>.design-decisions.md` carrying rationale
· `recordtype-diagrams.html` as a derived rendering · style, tone, formatting.

**Evidence contract:** ID · Severity · Kind · Claim (one sentence) · Evidence (`file:line` for every side,
verbatim quotes) · Checked (named explicitly) · Why (why it is wrong, not that two things differ) · Ruling
(the smallest question with options and consequences, or the correction proposed).

Full original prompt is in the session transcript; the six clauses above are the load-bearing ones.

---

## What to change if this is run again

**Partition by layer, not by bounded context.** This is the single highest-value change and § 7 of the
review argues it in full. Nineteen of twenty-one High findings were a `shared/` or `architecture/` file
disagreeing with the aggregate file it defers to — and a per-context subagent can only ever see half of
that. Suggested shape:

- **Pass 1 — `shared/` against its targets.** One agent per shared file, each reading that file against
  *every file it defers to*. `saga-patterns.md` → the three saga files. `cascade-rules.md` →
  `archive-fan-out.md` + the two Catalog write models. `cross-aggregate-invariants.md` → the aggregates in
  each rule. `event-store-and-messaging.md` → every context's § Consumed/§ Published. `api-permissions.md`
  → every `<agg>.api.md § Authorization`. `error-catalog.md` → every `**Errors:**` line.
- **Pass 2 — `architecture/` against the eleven aggregate specs.** `domain-model.md` per-aggregate section
  vs that aggregate's write model; `system-architecture.md` diagrams vs the saga and scenario files.
- **Pass 3 — per-context**, as run this time. Keep it: it is what produced § 6, and a review with no clean
  sections is not a review of the tree.
- **Pass 4 — navigation.** `README.md` and `glossary.md` as subjects: every map row against what its named
  file contains today, every Authority citation against a file that exists.

**Give every agent the three greps that worked**, and tell it they are leads:

```bash
# codes raised but not catalogued, and rows nothing raises — 11 candidates, 6 real
# (extract tokens on lines carrying **Errors:** or "errorCode", diff against the catalogue rows)

# permissions used but not declared — 2 candidates, 0 real (both stated absences)
grep -rhoE '`[A-Z][A-Za-z]+\.(Read|ReadWrite|Manage|Dispose)(\.All)?`' docs/spec --include=*.md

# plain-text .md references that resolve to nothing — how SC-042 was found
grep -rhoE '`[a-z-]+\.md`' docs/spec --include=*.md
```

**Tell it explicitly that two of three greps resolve on reading.** `Registration.Dispose` and
`ReviewerSelfApproval` both looked like findings and are both stated absences explained in the sentence
around them. That is trap 2, and it cost budget twice this run.

**Do not trust the guard, and check its patterns rather than its output.** Three of five checks have blind
spots (§ 7): `dates` misses year-month, `links` cannot see a plain-text file reference or an unclosed `](`,
and `structure` looks at the file's end so a mid-file truncation passes. Read
`.github/scripts/docs_guard.py` before quoting its result.

---

## Budget

Seven subagents, ~1.5 M subagent tokens, ~130 raw candidates, 49 reported. The two largest contexts
(Metadata ~5,900 lines including the HTML, Catalog ~8,100) each needed a full agent and used it. The
cross-cutting pass was done by the lead and took roughly a fifth of the total — it should be at least half
next time, for the reason above.
