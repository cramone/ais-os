# Pending edit to `review-cycle/SKILL.md` — severity vocabulary

**Status:** not applied. `Z:\claudia\magiq\.claude\skills\review-cycle\SKILL.md` is write-protected from
Cowork sessions, so this has to be pasted in by hand.

**Why:** the conformance pass of 2026-09-14 converted emoji severity markers to words in the nine editable
reviews. That forced a call on a fourth severity level the skill does not name but the register has always
used — X-11.30 and X-11.31 are graded **Critical**, and the prod-readiness gate's 🔴 tier maps onto them.
Chase's call was **keep `Critical` and amend the skill**, rather than flatten it to `High` and lose the
distinction. Until this lands, the tree and the skill disagree on this one point, deliberately, in the
tree's favour.

---

## The edit

In `## Finding ids and severity`, find:

```markdown
**Two scales, kept apart:**

- **Severity** — `High | Medium | Low`. A property of the finding. Every review, no exceptions, no emoji.
- **Gate status** — 🔴 / 🟠. A property of the *release decision*, owned solely by `type: gate` documents. Means "blocks the flag flip", not "is bad".
```

Replace with:

```markdown
**Two scales, kept apart:**

- **Severity** — `Critical | High | Medium | Low`. A property of the finding. Every review, no exceptions, no emoji.
- **Gate status** — 🔴 / 🟠. A property of the *release decision*, owned solely by `type: gate` documents. Means "blocks the flag flip", not "is bad".

**`Critical` was added 2026-09-14**, because the register had been using four levels while this section
named three. It is the top severity and it is narrow: a finding is Critical when the defect is live and
exploitable by a real caller, or destroys data that cannot be reconstructed. X-11.30 and X-11.31 are the
standing examples — any authenticated tenant member could confirm or reject another officer's statutory
filing. Everything that is merely bad and urgent is High. The gate's 🔴 tier and Critical often coincide,
but they remain different claims: Critical says *what the defect is*, 🔴 says *we will not flip the flag
while it is open*, and the gate alone makes the second call.
```

---

## A second amendment worth considering at the same time

Not applied, and not decided — raising it because the conformance pass ran straight into it.

**§ Frozen documents and the body conventions are mutually exclusive, and the skill does not say which
wins.** A `done` file takes no edits but additive `consumes` / `supersedes`. Eighteen of the twenty-seven
eligible reviews are `done`, so a "bring every review up to the required section structure" instruction
cannot be carried out without breaking the freeze. On 2026-09-14 the freeze won, leaving 7,839 lines and
31 emoji markers untouched by deliberate choice.

If that is the wrong default, the fix is a clause in § Frozen documents along these lines:

> **Formatting-only conformance edits are exempt.** Converting a severity marker to its word, renaming or
> re-levelling a heading, and adding a required section that states `none.` do not change what a document
> argues, so they may touch a `done` file. Anything that changes a finding, a severity level, a status or
> the scope of the document does not qualify. Report every such edit; a frozen file that changes should
> never do so silently.

**MM-040 is the case that makes this worth deciding.** It carries 18 of the 31 remaining markers, it is
the newest review in the tree, and it was `draft` — editable — right up until the same session closed it
to `done`. It is the first file to revisit if the exemption is adopted.
