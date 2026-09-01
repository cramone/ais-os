---
id: MM-024
type: plan
project: magiq-media
workstream: spec-drift-review
consumes: [MM-023]
depends-on: []
blocked-by-external: []
status: done
todo-id: 7ca3bb24-b8d6-5212-9cd6-455fd7a58a08
branches: []
ado: -
created: 2026-08-24
completed: 2026-08-25
---

> **Backfilled into the review cycle 2026-08-31 as MM-024.** **Done — all 31 units (W0–W30) and all six
> decisions (D1–D6) closed 2026-08-25.** Status flipped 2026-09-01, when a completion check found the work
> finished and only the bookkeeping stale. Nothing under `docs/` that this plan owns is known to be wrong;
> what remains is out of scope by §4 — the code findings in `spec-repo-drift-review.md`, the two parked
> workstreams (`asset-custody`, `projection-rebuild`), and **BI-1**, a decision about an unbuilt feature.

# DDD Spec Coverage — Remediation Plan

_Consumes `reviews/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` and
`reviews/spec-structure/spec-structure-recommendation-2026-08-25.md`._
_Drafted 2026-08-24 for Chase Ramone. **Restructured 2026-08-25** into resumable work units._
_Scope: `D:\source\github\magiq-media\docs\` — 72 spec files, 7 contexts, 21 ADRs. The aggregate count
is deliberately omitted: the spec gives three answers (9 / 10 / 12) and W7 reconciles it._

> **The work is not writing more spec. It is making the spec answer each question once, in a file that
> owns the question.** The coverage review found all 16 dimensions present somewhere; the structure
> review found that every dimension which spans aggregates is either duplicated across three-to-eight
> files or has no home at all. Those are the same problem seen twice.

---

## 1. Status board

**✅ Done.** The board below is a record, not a queue — every unit is ticked and every decision resolved.
The operating instruction it used to carry (*one unit per session; pick the first unblocked `☐`*) is kept
in §2 for the next plan that needs it.

> **Stale banner removed 2026-09-01.** This spot carried a 🚨 warning that `check-spec-sections.py`,
> `docs/spec/README.md` and `docs/spec/open-questions.md` were untracked while `docs-guard.yml` was
> committed calling one of them — red docs CI on `develop`. **All three are tracked and committed**
> (verified 2026-09-01), along with a fourth guard added since, `check-message-type-mirror.py` (X-4.15).
> The only uncommitted work under `docs/` is `adrs/deployment-and-resource-naming.md` plus a modified
> `adrs/README.md` — that is **W9's open choice** (write the ADR or delete the row), evidently acted on
> and not yet committed. It belongs to MM-004/DN-1, not to this plan.

**▶ Every W unit on this board is complete.** Thirty-one units, Stages A–E. **`check-spec-sections.py` reports `fail 0 · warn 16 · rename backlog 0`, and all 16 belong to BI-1** — every other owning unit is at zero. What remains is **not spec work**: the code findings in `spec-repo-drift-review.md`, two parked review workstreams (`asset-custody`, `projection-rebuild`), and **BI-1** — the bulk-import spec describing an unbuilt feature, which owns 16 of the 17 remaining CI warnings and is a decision about that feature rather than a documentation gap. (W24 and W28 needed W7, W25 needed W6; all three deps landed 2026-08-25). **No unit is blocked and no decision is outstanding** — D4 and D5 both resolved 2026-08-25. **Stage A and Stage C are complete**, and W19 released W20 and W21. **W6 and W7 both landed 2026-08-25.** `bounded-contexts.md` exists with both source files deleted;
`domain-model.md` now carries the single aggregate inventory and the three rules. W8 split `system-spec.md`
into five `shared/` files with no stub, releasing the five units behind it.

**All six decisions resolved 2026-08-25** — see §3. D1 (merge both architecture files, delete both) and D3
(`media.item.*`, the code wins) were the two that gated the spine; D4's premise turned out to be false, and
D5 was decided in favour of a complete authorization matrix rather than a privileged subset.

> **What W6 changed that later units depend on.** The host inventory now has **one** home
> (`bounded-contexts.md § Host Boundaries`) and the runtime shape has one (`system-architecture.md`).
> **All seventeen context relationships carry a type**, including the seven internal ones, which had none
> anywhere — every internal edge is Published Language over `media-cross-module-events` except
> **Metadata → Catalog, which is Conformist**. W20 and W24 should read that table before touching
> cross-context behaviour.

<details><summary>Board state when everything was blocked (2026-08-25, before D1/D3)</summary>

Twelve of the thirty-one units are done — all of Stage A, all of Stage C except W14, plus W5, W26 and W30.
Both CI guards run on every `docs/**` PR, three of their rules are flipped to `fail`, and the tree has
**zero unowned findings and an empty rename backlog**.

| Decision | Blocks | Then unblocks |
|---|---|---|
| **D1** — architecture-tier merge | **W6** | W7 → W8 → **W9, W10, W12, W14, W19** → W18, W20, W21, W24, W25, W28, W29 |
| **D3** — integration event naming | W11 | W27 |
| **D4** — `Capability` enum | W23 | — |
| **D5** — authorization matrix scope | W22 | — |

**D1 is the one that matters** — it gates seventeen of the nineteen open units, and its evidence is now
assembled: `bounded-context.md` is stale on topology but is the **sole owner** of the context-relationship
types, so the merge has a concrete must-carry-over list, and its four diagrams have already been redrawn
and corrected against the CDK.

**D3 is a five-minute read, not an investigation.** `open-questions.md#q-1` records that every
`[MessageType]` in the codebase is `media.item.*` and that `media.mediaitem.` appears nowhere in `src/`.
The decision is which spelling the spec keeps; the code already answered it.

</details>

### Carried forward — two register entries this plan could not close

Both are decisions rather than documentation gaps, so no unit could close them and neither blocks
archiving. They stay open in `docs/spec/open-questions.md`, verified still open 2026-09-01.

- **Q-4** ⚖️ **Infected object — delete or quarantine.** Not a documentation bug at all: the
  evidence-destroying hard-delete is **live shipping code** (`RecordValidationResultHandler`), the
  quarantine described in three spec files was never built, and `quarantine` appears nowhere in `src/`
  — while `media-quarantine` is provisioned and unwired (X-4.7). W10 corrected the spec to describe what
  ships and left the question open deliberately. **A product decision for regulated-records customers,
  and the one item here that gets worse the longer it waits.**
- **Q-11** 🔒 **MediaProfile scope.** `mediaprofile.api.md`'s authorization table promises an owner-scope
  check the code does not perform; `ListMediaProfilesQuery` filters on `TenantId` alone. W22 corrected the
  listing claim in two places, but the register entry closes only when the table matches the code **or**
  the code is changed to match the table — and which of those is right is Chase's call.

| ✓ | # | Unit | Size | Blocked by | Stage |
|---|---|---|---|---|---|
| ☑ | **W0** | Recover the truncated tails | — | — | *done 2026-08-25 — §9* |
| ☑ | **W1** | CI guard — no file ends mid-construct | ½ d | — | *done 2026-08-25 — found an 18th truncated file* |
| ☑ | **W2** | CI guard — required sections per file type | ½ d | W1 | *done 2026-08-25 — raised W30* |
| ☑ | **W3** | `spec/README.md` — the question map | ¼ d | — | *done 2026-08-25 — W6 must repoint rows 2, 3 & 10* |
| ☑ | **W4** | `open-questions.md` — contradiction register | ¼ d | — | *done 2026-08-25 — Stage A complete* |
| ☑ | **W5** | One canonical `glossary.md` | ¾ d | W3 | *done 2026-08-25 — 68 terms; W2 rule flipped to fail* |
| ☑ | **W6** | Reconcile the architecture tier — 3 files, 3 answers | 1½ d | — | *done 2026-08-25 — closed Q-14* |
| ☑ | **W7** | `domain-model.md` — inventory, relationships, the rules | 1 d | — | *done 2026-08-25 — 9 aggregates, settled* |
| ☑ | **W8** | Split `system-spec.md` | 1 d | — | *done 2026-08-25 — released 5 units* |
| ☑ | **W9** | `_Last reviewed:` + kill dangling references | ½ d | — | B · One answer |
| ☑ | **W10** | Sweep within-file contradictions (Tier 3) | ½ d | — | B · One answer |
| ☑ | **W11** | Integration event naming — decide, delete, ADR | ½ d | — | B · One answer |
| ☑ | **W12** | Read-model table names against the CDK | ¼ d | — | B · One answer |
| ☑ | **W13** | DDD-T11 · RecordType uniqueness contract | ½ d | — | *done 2026-08-25 — found X-4.16 (High)* |
| ☑ | **W14** | DDD-T16 · DR runbooks | ½ d | — | *done 2026-08-25* |
| ☑ | **W15** | DDD-T10 · MediaItem asset subscriptions | ¼ d | — | *done 2026-08-25 — documented a reference model that had none* |
| ☑ | **W16** | DDD-T12 · ProcessingJob mirror rules | ¼ d | — | *done 2026-08-25 — found X-4.17* |
| ☑ | **W17** | DDD-T17 · `workflow_dispatch` docs | ¼ d | — | *done 2026-08-25 — 1 marker left tree-wide* |
| ☑ | **W18** | Delete `docs/spec/_recovered/` | 5 min | — | *done 2026-08-25 — guard now unconditional* |
| ☑ | **W19** | `sagas/` file type + `AssetIngestionSaga` | 1½ d | — | *done 2026-08-25 — bypass hole was a false alarm; found X-11.5/11.6/11.7* |
| ☑ | **W20** | Delete `MediaItemReviewSaga` from 4 files *(it was 11)* | ½ d | — | *done 2026-08-25 — "never built" was false; closed Q-2 and Q-13* |
| ☑ | **W21** | `DocumentSigningSaga` + the two fan-out workers | 1 d | — | *done 2026-08-25 — the fan-out half found 5 live findings, 2 High* |
| ☑ | **W22** | Authorization matrix — **complete**, privileged first | 3 d | — | *done 2026-08-25 — **86 of 132 commands unguarded; two Critical escalations*** |
| ☑ | **W23** | MediaItem's three state machines, one table | 1½ d | — | *done 2026-08-25 — closed G-4, Q-6, Q-9, Q-10; found X-11.34/35/36/37* |
| ☑ | **W24** | Cross-aggregate invariants + cascade rules | 1 d | — | *done 2026-08-25 — closed G-2 and G-3; the ADR was wrong in four places* |
| ☑ | **W25** | `shared/consistency-model.md` | ½ d | — | *done 2026-08-25 — G-6 closed; 10 warnings cleared* |
| ☑ | **W26** | The three missing `scenarios.md` | 1 d | — | *done 2026-08-25 — raised X-11.2, X-11.3* |
| ☑ | **W27** | Retire `BULK-IMPORT-SPEC-UPDATES.md` | ½ d | — | *done 2026-08-25 — 467 lines, one section worth keeping* |
| ☑ | **W28** | Apply the entity-vs-VO rule | ½ d | — | *done 2026-08-25 — 3 of the 5 named types do not exist* |
| ☑ | **W29** | Tier 2 client-contract sweep | 1 d | — | *done 2026-08-25 — idempotency exists; 9 findings, 3 High* |
| ☑ | **W30** | Close the 19 unowned section gaps + 35 renames | 1½ d | W2 | *done 2026-08-25 — 0 unowned, 0 renames; raised X-11.4* |

**Blocked-by includes decisions.** A unit showing **D3**/**D4**/**D5**/**D1** is not startable until §3
records that decision as resolved, however clear its own steps look.

**≈21¾ days** — A 1½ · B 6 · C 1¾ · D 7½ · E 5. Stage A is the cheapest in the plan and unblocks
everything; its four units are what stop the spec re-growing duplicates while the rest is worked.
*(Stage E grew by W30's 1½ d on 2026-08-25 — W2's measurement found 19 section gaps no unit owned. A guard
that measures the tree will do this: it is the plan meeting the spec as it is rather than as the reviews
described it. The headline also gained ¼ d in arithmetic correction — the stage figures always summed to
21¾ once W30 was added, and to 20¼ rather than 20 before it.)*

**Not in this plan, deliberately:** **X-11.1** — the traceability tables name 4 projector classes that do
not exist, **88 times** across `docs/spec/` (`MediaItemProjector` 41 · `CollectionProjector` 18 ·
`AssetProjector` 16 · `SigningSessionProjector` 13). Owned by `spec-repo-drift-review.md` per §4. Several units below
touch those tables; correct what you touch, but the sweep is not yours.

---

## 2. Session protocol

1. **Pick the first unblocked `☐` on the board.** Do not batch units — each is sized to finish.
2. **Read the unit.** Where a unit needs context beyond its own steps it carries a *Read first* list;
   most do not, and those are self-contained. Only W1 and Stage C send you to the appendix, and both say
   so explicitly.
3. **Work the unit's checkboxes.** Tick them in place as you go, so a session that runs out of room
   leaves a half-done unit legible rather than a lost one.
4. **Verify against code, not against a sibling spec file.** The single most expensive assumption in this
   tree is that another spec file is right. Handlers, projectors, endpoint classes and the CDK are the
   arbiters. Cite what you derived from, in the file, the way the 2026-08 correction notes do.
5. **Disagreement between code and spec about *behaviour* is a new drift finding.** File it in
   `spec-repo-drift-review.md`; do not silently pick a side. Naming mismatches you may just fix.
6. **A question you cannot settle goes in `open-questions.md`** (W4), not in a comment and not in a
   Slack message. If W4 is not done yet, that is a reason to do W4 early.
7. **Close the unit:** tick it on the board, add one line to §8, and note anything the next session needs
   to know that is not already written down.

> **Never rewrite a whole spec file in one pass.** Edit in place, section by section. Wholesale rewrites
> are what truncated 18 files (§9). W1's guard has landed and will catch a bare cut on any PR touching
> `docs/**` — but it catches the loss, it does not undo it. Editing in place is still the actual defence.

---

## 3. Decisions

| # | Decision | Status |
|---|---|---|
| **D1** | **Authority model** — rewrite the stale architecture docs, or demote them? | **Resolved 2026-08-25 (Chase).** Merge both into `architecture/bounded-contexts.md` and delete both, `service-boundaries.md` as the base. **Carry over `bounded-context.md`'s `### Context Relationship Types` table** — it is the only relationship-type table in the tree and `service-boundaries.md:27` explicitly delegates to it. W7 rebuilds `domain-model.md`. **Unblocks W6.** |
| **D2** | ~~Truncated tails — rewrite from code, or mark and rewrite later?~~ | **Resolved 2026-08-25.** Search history first, then date what you find. 15 of 17 tails recovered: 12 restored, 3 quarantined because they predate the correction pass, 2 unrecoverable. §9. |
| **D3** | **Integration event naming** — `media.mediaitem.*` (16 uses) or `media.item.*` (12)? | **Resolved 2026-08-25 (Chase). `media.item.*` — the code wins.** Every `[MessageType]` in the codebase is `media.item.*` and `media.mediaitem.` appears nowhere in `src/`. Delete the losing spelling from all five spec files that carry it — `bounded-context.md`, `service-boundaries.md`, `Catalog/context-overview.md`, `DocumentSigning/context-overview.md`, `documentsigningsession.scenarios.md` — plus `system-spec.md`'s Billing row and sample payload. **Do not alias**; external SNS filter policies cannot be written against both. Write the ADR. **Unblocks W11.** Evidence in `open-questions.md#q-1`. |
| **D4** | **`Capability` enum** — API allows 4 values, write model defines 9, defaults seed 2 the API rejects. | ☑ **Resolved 2026-08-25 — the premise was false; no decision needed.** Verified against code: there is **one** `Capability` enum with **nine** values (`Registration`, `CheckInOut`, `Retention`, `Review`, `Processing`, `Distribution`, `Governance`, `VersionControl`, `Signing`), and **the endpoint and the command use that same type** — `SetCapabilitiesRequest.Capabilities` is `List<Capability>`. There is **no restricted four-value list anywhere**; every parse site is `Enum.Parse`/`TryParse` over the full enum. The seeded defaults use `Processing`, `VersionControl`, `Review`, `CheckInOut`, `Registration` — all valid. So the API rejects nothing the write model allows and nothing the defaults seed. **What remains is a pure documentation gap** — the enum is specified nowhere — which is W23's step, not a decision. **W23 unblocked.** |
| **D5** | **Authorization matrix scope** — all ~150 commands, or the privileged subset first? | ☑ **Resolved 2026-08-25 by Chase: comprehensive.** *"Cover at least all the ones that make sense according to best practice and any additional ones that should be included — I don't want to miss any."* So the matrix is **complete, not a subset**: every state-changing command gets an explicit, documented authorization rule derived from code. Privileged commands are still written **first**, because they carry the risk and because an incomplete matrix that stops there is the failure mode this decision rejects — but the unit does not end until every command is classified. **Completeness is the acceptance test:** a command absent from the matrix must be absent because it does not exist, not because nobody reached it. Anything the code does not enforce escalates as a security finding rather than being written up as behaviour. **W22 unblocked.** |
| **D6** | Does this plan own the `MediaItemReviewSaga` deletion? | **Resolved.** Yes — W20. It is a spec-consistency fix across four files and the drift review has no finding for it. |

---

## 4. Ownership boundary with the drift review

`plans/spec-drift-review/spec-repo-drift-review.md` is the sibling checklist in this folder. Where a
finding is already an X-finding there, **the drift review owns it and this plan does not restate it.**

| Finding | Owner |
|---|---|
| DynamoDB key shapes diverge between the two tables *(DDD review finding, not a truncation id)* | Drift review — X-4.10 / X-4.11–4.13 |
| Error-catalog gaps | Drift review — X-10.1 / X-10.2 / X-10.3 |
| Idempotency headers absent from OpenAPI | Drift review — X-10.5 · **this plan** for the spec's claim that it exists (W29) |
| Bulk import aggregates specced with no code | Drift review — BI-1 / BI-2 / BI-3 · confirmed from the spec side 2026-08-25 |
| **Projector class names do not exist, 88 spec references** | Drift review — **X-11.1**, raised 2026-08-25 by this plan's code check |
| Host inventory 8 vs 9 vs 12 | Drift review — X-1.1 · **this plan** removes the stale copies (W6) |
| Review saga specified four ways | **This plan** — W20 |
| `ITenanted` vs `ITenantScoped` | **This plan**, spec side only — W10 |
| Everything else in the DDD and structure reviews | **This plan** |

> When either plan closes something the other cites, note it in both. Two checklists over one spec tree is
> the failure mode this table exists to prevent.

---

## 5. The units

Effort is working days for one person who knows the codebase, excluding review cycles.

---

### Stage A · Guard and orient

*Nothing later survives without these, and they are the cheapest units in the plan. A3 and A4 exist
because every duplicated section in this spec was written by someone who needed an answer, could not tell
which file owned it, and wrote it where they were standing.*

#### W1 · CI guard — no file ends mid-construct · ½ d · needs nothing

**Goal.** Make the truncation that damaged 17 files a build failure instead of a discovery.

**Read first.** §9 (what the cutter does and why it lands where it does).

| ✓ | Step |
|---|---|
| ☑ | New workflow in `magiq-media`, its own file — **not** inside `build-and-push.yml`. A spec typo must not block an image build. Trigger on PRs touching `docs/**`. |
| ☑ | Fail if any `docs/spec/**/*.md` lacks a trailing newline, or if its last non-blank line ends mid-construct: unclosed backtick, table row without a closing `\|`, heading with no body, link with no closing `)`. |
| ☑ | **Allowlist the marked exceptions:** a file may end mid-construct only when its last block is a `⚠ TRUNCATED` note. Five files qualify today (DDD-T10, T11, T12, T16, T17); all five are gone by W18. |
| ☑ | **Skip `docs/spec/_recovered/`** — quarantined salvage with deliberately unresolvable links and one mid-table cut. The folder is deleted at W18; the exclusion can go with it. |
| ☑ | Add the rule to the repo `CLAUDE.md`: **never rewrite a whole spec file in one write.** Edit in place; large files section by section. This is what cut them. |

**Done when.** The check fails against `docs/spec/` as it stood on 2026-08-24 and passes against it today.
*Build it against the 2026-08-24 tree — run against today's it passes vacuously and proves nothing.*

**Touches.** `.github/workflows/`, `CLAUDE.md`.

**Done 2026-08-25.** `.github/workflows/docs-guard.yml` runs
`.github/scripts/check-spec-truncation.py` on every PR touching `docs/**`, on pushes to `develop`/`main`,
and on manual dispatch. Built against `23b56e82` (the 2026-08-24 tree) as §2 requires, not against today's.

Nine rules, each of which fires on real damage in that tree — no rule was written speculatively:
`no-trailing-newline` ×22 · `unclosed-inline-code` ×6 · `unclosed-link-target` ×3 ·
`unterminated-table-row` ×2 · `unclosed-link-text` ×2 · `heading-with-no-body` ×2 ·
`unterminated-prose` ×1 · `unclosed-code-fence` ×1 · `empty-list-item` ×1.

**Verdicts:** 2026-08-24 tree → fail, 40 findings across **23** files. Today's tree → pass, 72 files.
The 23rd file is new — see below.

Three things worth carrying forward:

- **Balance inline constructs over the trailing *block*, not the last line.** Emphasis and inline code
  legally wrap across lines; `mediachangerequest.api.md`'s recovery note opens `**Route parameter` on one
  line and closes `corrected on restore:**` on the next. Judged per-line that healthy pair reads as an odd
  marker count. A truncation is still caught, because the cut removes the closing half from the block just
  as surely as from the line.
- **`unterminated-prose` exempts list items.** The `## Related` lists that close most files end on an
  unpunctuated gloss, so the rule fired on six healthy files. Nothing is lost: every truncated list item in
  the 2026-08-24 tree was already caught by the bracket, backtick or empty-bullet rules, because a cut
  inside a list lands inside a link far more often than after one.
- **The `⚠ TRUNCATED` allowance is not redundant, but not for the obvious reason.** The end-of-file rules
  already pass on all five marked files — the note is a well-formed blockquote a blank line below the cut,
  so they never look at the cut text. What the allowance actually buys is the whole-file rule: a file cut
  open inside a code fence stays open no matter what is appended after it. Keep it until the last marker
  is gone at W18.

**The guard found an 18th truncated file on its first run — `mediaitem.read-model.md`.** It ends inside an
unclosed ` ```csharp ` block. It was missed on 2026-08-25 because it **kept its trailing newline** — the
only damaged file that did — so it never appeared in the 22-file list of §9.1 and no marker was placed on
it. It has been cut since `d0adc7bc` ("Status Code Review (#158)", **2026-07-19**) — five weeks, through
both the 2026-08-24 correction pass and the recovery pass. This is the case the guard exists for: a cut
that leaves no fingerprint a human scan would catch.

Recovered from `6fc139ee` ("Docs/create (#153)", 2026-07-07), the last commit on this branch's history
carrying the whole tail: the closing fence, a `MediaItemStatus` enum and the `## Related` link list.
Restored, with the enum **corrected against `Catalog.Domain/.../ValueObjects/MediaItemStatus.cs`** — the
recovered text lists four members, omits `Revising`, and omits the pinned numeric values, which are part
of the stored event contract. Restoring it verbatim would have injected a wrong enum. Provenance is in the
file, per §2 step 4.

> **Cite reachable commits.** The pre-squash feature-branch objects `9381b7e9` (2026-07-18) and `402de9d5`
> (2026-07-16) carry byte-identical blobs and were what the search actually surfaced, but neither is an
> ancestor of any branch — they disappear on a fresh clone or after GC. The equivalents on the shipped
> history are `d0adc7bc` and `6fc139ee`. §9.4 should gain this step: a recovered blob is only useful
> provenance if the commit naming it survives a clone.

> **This changes the counts in §9.1**, which is annotated accordingly: 23 damaged, **18** truncated (not
> 17), 5 newline-only (unchanged — the correction adds a truncated file, not a newline-only one). The
> 22-file list was assembled by looking for missing trailing newlines, and that is not the same population
> as "files that end mid-construct" — which is exactly why the guard has `unclosed-code-fence` as a
> whole-file rule rather than an end-of-file one.

**Note for W10.** `MediaItemStatus` membership is on W10's sweep list. One instance is now settled with
its source cited; the rest of the tree is untouched and still W10's.

**Note for W18.** Two things to remove, not one: the `_recovered/` path in `EXCLUDED_DIRS` **and** the
`ends_with_truncation_marker` early return. Both are commented in the script with this instruction.

---

#### W2 · CI guard — required sections per file type · ½ d · needs W1

**Goal.** Turn "the 16 dimensions are covered" into a build result rather than an opinion. Heading
presence only — cheap, and it catches the omission that matters (a saga file with no transition table).

**Read first.** `reviews/spec-structure/…-2026-08-25.md § 4` — the full contract table.

| ✓ | Step |
|---|---|
| ☑ | Extend W1's workflow: match file by name pattern, assert required `##` headings present. |
| ☑ | `<agg>.write-model.md` → `Purpose` · `Invariants` · `Properties` · `Value Objects` · `Status transitions` · `Methods (Commands)` · `Domain Events` · `Handler-side Pre-conditions` · `Published Integration Events` · `Consumed Integration Events` · **`State Machine Interaction`** *(required only where the aggregate has more than one state machine — MediaItem has three; W23 delivers it)*. |
| ☑ | `<agg>.read-model.md` → `Read Models` · `Projection Handlers` · `Queries` · `Read Model Types` · `Consistency`. |
| ☑ | `<agg>.api.md` → `API Conventions` · `Authorization` · `Write Endpoints` · `Read Endpoints` · `Command → Event → Projection Traceability` · `Related`. |
| ☑ | `<agg>.scenarios.md` → `Index` · `Diagram Key` · ≥1 scenario · `Related`. *(≥1 scenario is not checked — a heading-presence check cannot count scenarios, and `Index` + `Diagram Key` are only written when there are some.)* |
| ☑ | `context-overview.md` → `Purpose` · `Responsibilities` · `Aggregate List` · `Service Boundaries` · `High-Level Event Flows` · `Integration Event Contracts` · `Related Specifications`, plus **fail if a `Ubiquitous Language` heading is present** — that section belongs to `glossary.md`. **Ship this one rule as a warning until W5 lands**, or it fails 6 of 7 overviews on day one for work nobody has done yet. |
| ☑ | `sagas/<saga>.md` → `Purpose` · `Correlation Key` · `State Table` · `Transition Table` · `Timeouts` · `Compensation` · `Idempotency` · `DLQ & Poison Policy` · `Manual Intervention Runbook`. *(Contract is in the script; no file matches it until W19 creates `contexts/<Ctx>/sagas/`.)* |
| ☑ | Every file → `_Last reviewed:` line. **Warn, don't fail, until W9 lands** — 72 files lack it today. |
| ☑ | Expect failures on day one and record them: 3 aggregates have no `scenarios.md` (W26); **no** `Consistency` section exists anywhere (W25); `Folder` has no `Value Objects` (W28); `mediaitem.write-model.md` has no `State Machine Interaction` (W23); 6 context overviews still carry `Ubiquitous Language` (W5, warned not failed). That list *is* the backlog, and it should match the board. |

**Done when.** The check runs on every `docs/**` PR, and every failure it reports maps to a `☐` on the
board — no unexplained red. It is not expected to be green until Stage E closes.

**Touches.** `.github/workflows/`.

**Done 2026-08-25.** `.github/scripts/check-spec-sections.py`, wired as the second step of
`docs-guard.yml`. Contract encoded verbatim from the structure review § 4, including the `saga` contract
that no file matches yet — so the first saga file W19 writes is measured against the contract rather than
against whatever its author remembered.

**This unit's prediction was wrong, and the correction is the finding.** The step above expected five
categories of day-one failure. The first measurement found **53 missing sections across 31 of 72 files**.
The contract was written from `mediaitem.write-model.md` — the best-formed file in the tree — and most
files never matched it.

So **"every failure maps to a ☐ on the board" was unreachable as written**, and two decisions were taken
rather than forcing it (Chase, 2026-08-25):

1. **Everything ships at `warn`; each unit flips to `fail` when it closes.** The plan already prescribed
   exactly this for `_Last reviewed:` (until W9) and `Ubiquitous Language` (until W5) — this generalises it
   rather than inventing it. A check that is red from the day it lands is a check people learn to ignore.
   `continue-on-error` is deliberately **not** used in the workflow: the script's exit code is the switch,
   so the day a unit flips, CI starts failing with no workflow edit.
   **Severity is keyed by owning unit, not by rule** (`OWNER_SEVERITY`). Keying by rule was tried first and
   does not work: W25, W28, W22, W30 and BI-1 all report through the single `required-section` rule, so
   flipping that one line turns on ~50 findings at once — including the 15 BI-1 has explicitly deferred.
   Keyed by unit, a closing unit flips exactly its own column. Verified: flipping `W25` to `fail` yields
   10 failures and exit 1; everything else stays warn.
2. **Synonyms are accepted and logged.** Six write-models say `## Status Lifecycle` where MediaItem says
   `## Status transitions`; `## Command Handlers` answers `Handler-side Pre-conditions`; `## Read Model
   Tables` answers `Read Models`. A curated `SYNONYMS` map accepts these so the check measures *coverage*
   rather than spelling, but a file matching only by synonym is reported as a `non-canonical-heading` note
   — never affecting the exit code. **That is a 35-item rename backlog, now visible and countable instead
   of silently blessed.** Run with `--show-renames` to see it.

**A first pass at the synonym map produced 6 false gaps, and finding them mattered more than the map.**
Verification against the files themselves — not against the map — caught: `## Handler Pre-conditions`
(unhyphenated, 3 files) was simply absent from the map; and three write-models give each value object its
own section (`## RegistrationItem Value Object`, `## FieldDefinition Value Object`), a *suffix* form that
prefix matching can never reach. Both fixed — `CONTAINS_FORMS` handles the suffix case. Two synonyms were
also **removed as unsound**: bare `Status` and `Lifecycle` would let `### Status codes returned by the API`
satisfy `Status transitions`. Neither was load-bearing.

> **The lesson generalises, and it is the same one as §7's.** A synonym map is a claim about the spec that
> is just as capable of being wrong as the spec is. Every entry here was checked by opening the files that
> use it, and one round of that check moved the unowned count from 22 to 19 and W28's from 5 to 2. **Do not
> add a synonym without reading the section it claims to match.**

**Every finding names its owning unit.** The script prints the owner against each line and totals by unit,
so the report *is* the backlog and nothing can sit unowned unnoticed. Day-one attribution:

| Owner | Findings | Matches the prediction? |
|---|---|---|
| **W9** | 72 | ✅ every file lacks `_Last reviewed:` |
| **BI-1** | 14 | new — see below |
| **W25** | 10 | ✅ no `Consistency` section exists anywhere |
| **W5** | 6 | ✅ exactly the 6 context overviews |
| **W26** | 3 | ✅ the 3 aggregates with no `scenarios.md` |
| **W28** | 2 | ⚠️ predicted 1 (Folder); it is 2 — **Collection too, and W28's steps do not name it** |
| **W22** | 1 | new — a missing `Authorization` section is W22's input |
| **W23** | 1 | ✅ `mediaitem.write-model.md` |
| **unowned** | **19** | **new — needs W30** |
| *rename backlog* | *35* | *informational, never fails* |

*(128 warnings total. Run the script for the live figures — these are the day-one snapshot.)*

**Two ownership rules are encoded in `OWNER_OVERRIDES`, both judgment calls worth knowing about:**

- **The two bulk-import aggregates → BI-1 (15 findings).** Not one command or projector exists behind
  them (§9.3, drift review BI-1/BI-2/BI-3). Their missing sections are not documentation debt; they are
  downstream of aggregates that were never built. Writing that spec now is writing spec for code that may
  never ship — which is the thing BI-1 has to decide first. Deferred, not swept.
- **Missing `Authorization` sections → W22.** W22 rebuilds the matrix from endpoint attributes and handler
  guards; a missing `Authorization` heading is its input, not a separate heading-filling job racing it.
- `_Last reviewed:` and `<missing scenarios.md>` are in `PATH_INDEPENDENT` so a path override cannot claim
  them — W9 dates *every* file, and W26's steps name all three missing `scenarios.md` including both bulk
  ones (its step says coordinate with BI-1/BI-2, not hand them over). Without this, a bulk-import file's
  missing date line would have been attributed to BI-1.

**Not done, deliberately:** `≥1 scenario` in the `scenarios.md` contract. A heading-presence check cannot
count scenarios, and the `Index` and `Diagram Key` rules already fail an empty file.

---

#### W3 · `spec/README.md` — the question map · ¼ d · needs nothing

**Goal.** The highest-value file in this plan and the cheapest. Not an index of files — an index of
*questions*, with a **"Not"** column naming the file people wrongly open.

**Read first.** `reviews/spec-structure/…-2026-08-25.md § 3`.

| ✓ | Step |
|---|---|
| ☑ | Create `docs/spec/README.md`: one table, *question → the one file that answers it → not this one*. |
| ☑ | Cover at minimum: term definitions · which context owns X · what commands an aggregate accepts · what a route does · how a long-running process ends · how stale a read can be · what is still contested · what has been decided and why (→ `docs/adrs/`, a sibling of `docs/spec/`, not inside it). |
| ☑ | Point rows at files that do not exist yet (`glossary.md`, `open-questions.md`, `consistency-model.md`, `sagas/`) and mark them **planned**. A map that shows the gaps is more useful than one that hides them, and it stops the next person inventing a home. |
| ☑ | Link it from the repo `CLAUDE.md` § *Spec and architecture — source of truth*. |

**Done when.** Someone who has never opened this spec can find the owner of any of the 16 dimensions in
one hop.

**Touches.** `docs/spec/README.md`, `CLAUDE.md`.

**Done 2026-08-25.** All 16 dimensions have a row, plus four extras the review's sketch did not have:
cross-aggregate invariants (7b), MediaItem's state-machine interaction (9b), cross-aggregate references
(10b), and build/deploy. Every planned row **says where the answer lives today** rather than only naming
the file that will own it — a map that answers "nowhere yet" for a live question is not a map.

Three decisions worth knowing:

- **No `W`-numbers in the file.** Planned rows are marked *(planned)* and tracked "in the docs project and
  on the `Media` ADO board". Citing `W5` in a repo file would point Estelle and Akshay at a plan on `Z:\`
  that they cannot open — which is the exact failure W4 exists to fix. Not worth reintroducing it in the
  file whose job is to orient them. **But the substitute is weak** — "tracked on the board" gives them
  nothing to click. **W4 should fix this properly:** `open-questions.md` is in-repo and exists precisely
  so non-Chase engineers can see what is unresolved, so each *(planned)* row should end up citing
  `open-questions.md#Q-n`. That is a real anchor for all three engineers and costs W4 nothing extra.
- **Rows point at the files that exist today, not the post-merge ones.** A map whose rows are false on the
  day they are read is worse than no map. **W6 must repoint rows 2, 3 and 10** when it lands, and delete
  the `bounded-context.md` mentions from their *Not* columns — noted here and in W6 because it is easy to
  merge two files and forget the map. Row 3's *Read* target is `domain-model.md`, which is **W7's**, not
  the merge's.
- **A closing section names what a careful reader would otherwise be caught by**: the phantom
  projector-class references (X-11.1), the heading variance W2 measured — with the real per-section rates,
  not a hand-wave — and the five `⚠ TRUNCATED` markers. Ending on "when the spec and the code disagree,
  the code wins and the spec has a bug" is §2 step 4, stated where a non-plan-reader will see it.

> **Verification caught three factual errors in the first draft, and their common cause is worth naming.**
> All three were **inherited from the structure review's §1 and stated more confidently than the review
> stated them.** ① Row 10 pointed at `service-boundaries.md` for context relationships and told readers
> *not* to open `bounded-context.md` — but `bounded-context.md § Context Relationship Types` is the **only**
> table of relationship types in the tree, and `service-boundaries.md:27` explicitly delegates to it. The
> map forbade the one file that answers the question. ② "`service-boundaries.md` **explicitly repudiates**
> `bounded-context.md`" is false: it repudiates *its own* 2026-03-11 predecessor. ③ The three disagreeing
> aggregate inventories are `domain-model.md` (10), `bounded-context.md § Command Handler — Aggregates
> Owned` (9) and the seven context overviews (12) — **not `system-architecture.md`**, whose twelve-item
> list is the *host* inventory behind X-1.1. All three fixed.
>
> §2 step 4 says verify against code, not against a sibling spec file. **This is the same rule one level
> up: a review is not evidence either.** The reviews are the best reading of this tree anyone has done and
> they are still wrong in places — W6 inherits errors ① and ② directly, since its step list repeats the
> repudiation claim.

**Also linked from `docs/README.md`**, not just the repo `CLAUDE.md`. `CLAUDE.md` is what an agent reads;
`docs/README.md` is what a person lands on. Both now point at the map in their first few lines.

**New finding, filed for W9 — a second file that has never existed.** `docs/adrs/README.md` lists a topic
document **`deployment-and-resource-naming.md`** in its "Current decisions, by topic" table, covering
environment-agnostic resource naming. `git log --all` finds **no revision of that path in any branch** —
same shape as `specs/media-management-domain-spec.md` in W6/W7. Either the decision was made and never
written up, or the row is aspirational. A full relative-link sweep of `docs/` found only **3** dangling
links tree-wide, and **none inside `docs/spec/`**: this one, an ADR-010 archive link to a
`repos/magiq-media/...` path, and `breaking-changes.md → ../../RUNBOOK.md`. That is a much cleaner result
than W9 assumes, and W9 should start from this list rather than re-deriving it.

---

#### W4 · `open-questions.md` — contradiction register · ¼ d · needs nothing

**Goal.** Give a known-unresolved disagreement somewhere to live **in the repo**. They currently
accumulate in review documents on `Z:\`, which per the repo's own `CLAUDE.md` is Chase's machine only —
**Estelle and Akshay cannot see the list of things the spec is wrong about.**

**Read first.** `reviews/spec-structure/…-2026-08-25.md § 5`; the DDD review's §5 contradiction register.

| ✓ | Step |
|---|---|
| ☑ | Create `docs/spec/open-questions.md`: `#` · question · sides · status · owner · opened. |
| ☑ | Seed it from the DDD review's Tier-1 contradictions — integration event naming (D3), `Capability` enum (D4), Approve authorization specified three ways, MediaProfile owner-scoped listing (security-relevant), read-model table naming. |
| ☑ | State the closing rule in the file: **an entry closes by being deleted**, with the winning rule written into the owning file. No "resolved" section — that is how a register becomes a second spec. |
| ☑ | Add a row to `spec/README.md`'s table pointing at it. *(Row 14 already exists and points here — check it rather than adding a second.)* |
| ☑ | **Give every *(planned)* row in `spec/README.md` an anchor here.** W3 marked six rows *(planned)* and could only say they are "tracked in the docs project and on the `Media` ADO board" — nothing Estelle or Akshay can click, because the plan is on `Z:\`. Registering each planned file as a `Q-n` entry and citing `open-questions.md#Q-n` from the row makes the map actionable for all three engineers, in-repo, at no extra cost. This is the same problem this unit exists to solve, one level up. |

**Done when.** Every Tier-1 contradiction is visible to someone with only repo access, and each names an
owner.

**Touches.** `docs/spec/open-questions.md`, `docs/spec/README.md`.

**Done 2026-08-25.** `docs/spec/open-questions.md` — **all 14 Tier-1 contradictions** as `Q-1`…`Q-14`,
plus a second section of six **known gaps** (`G-1`…`G-6`) for the questions with no owning file. Twenty
anchors, all reachable from `README.md`; row 14 now links to a file that exists, and every *(planned)* row
carries a `#g-n` anchor instead of pointing at a plan on `Z:\`.

**All 14 were verified against the spec and the code before being written down.** The step above named
five to seed; seeding only those would have hidden the two entries with the sharpest consequences —
neither is in that list:

- **Q-4 ⚖️ — a live compliance exposure, not a spec bug.** `asset.write-model.md` says the handler **must
  hard-delete** the infected S3 object; `asset.scenarios.md` and `system-spec.md` say it moves to
  `media-quarantine`, *not deleted*, because regulated-records customers need the object to survive and
  deleting it destroys the audit trail. **The delete is what ships.** See the note below — this one
  changed shape once it was checked against code.
- **Q-12 🔒 — the only place in the system where `TenantId` comes from a table rather than
  `IExecutionContext`**, on an unauthenticated webhook. Two files specify different lookup tables and the
  read model explicitly rejects the one the write model names as "eventually consistent and unsuitable for
  a security decision". Not deployed, but the write model is what an implementer would build from.

**Three entries turned out to be different from the review's account, and the verification is why:**

| | The review said | What the tree actually shows |
|---|---|---|
| **T3 → Q-3** | Two architecture files vs AssetManagement | `service-boundaries.md` **contradicts itself** — it states the reconciled S12 rule in one place and the full-pipeline claim in another |
| **T8 → Q-8** | `system-spec.md` vs `system-architecture.md` | `system-spec.md`'s main inventory is **already corrected**; only its projector table still says `-detail`. The CDK settles it outright: `read-models.construct.d.ts` states the singular rule and no `*-detail` table is provisioned |
| **T11 → Q-11** | `api.md` documents a `caller.owner_id` check | The **endpoint body is already fixed**; what survives is the **authorization table**, which still promises owner scoping the code does not enforce. The residual risk is false assurance, not a described-but-absent check |

**Nine of the fourteen are settled by evidence that already exists** — six by code, one by the CDK, two by
a spec file that carries the reconciled note. Each entry's *Settled by* line names that authority.

> **Honest caveat on the "no second spec" rule.** Four entries — Q-6, Q-8, Q-10, Q-13 — do more than
> point: Q-6 lists all nine enum members, Q-8 and Q-10 quote the rule and the code comment, Q-13 states the
> winning authorization rule. That is a mild breach of the plan's warning, kept deliberately because those
> four are the ones a reader most needs settled on the spot. **It is a debt, not a design:** when each
> closes, the restatement goes with it. Do not extend the pattern to new entries.

> ⚠️ **Q-4 was rewritten after verification, and the correction reverses its character.** The first draft
> said "neither behaviour is implemented" — that is false. `RecordValidationResultHandler` calls
> `s3.DeleteObjectAsync` on `VirusDetected` today, six further code sites document deletion as the
> contract, and `quarantine` appears **nowhere in `src/`**. So the evidence-destroying side is the one in
> production, and the three spec files describing quarantine-for-forensics describe something never built.
> **Every other entry here is a documentation bug where the code is already right; Q-4 is the reverse.**
> It is a product decision for regulated-records customers, not an editing task, and the entry now says so.
>
> The error came from trusting `asset.scenarios.md`'s own note that "no code performs the move and the
> Processing Worker's role holds neither `s3:PutObject`…" — true, but about the *quarantine move*. The
> delete happens in the **Api write host**, which that note never mentions. **A spec file's disclaimer
> about what code does is still a spec claim**, and §2 step 4 applies to it exactly as it does to the rest.

**Owner is "Chase" on every row, deliberately.** Not `W11`/`W22`/`W23` — those point at a plan on `Z:\`
that two of three engineers cannot open, which is the failure this unit exists to close. The file says
owner means *who decides*, not who edits.

**Also fixed:** `architecture/bounded-context.md` began `z# Bounded Context Map…` — a stray leading
character breaking the H1, so the file had no title in any renderer. One-character fix.

**Note for W6.** `bounded-context.md` carries **2** correction notes against `system-architecture.md`'s 7,
while sitting on the losing side of **five** of these entries (Q-1, Q-3, Q-5, Q-8, Q-14). It looks like it
was skipped by the 2026-08-24 correction pass. Treat every claim in it as unverified during the merge —
including the ones that look like they survived.

---

### Stage B · One answer per question

*The DDD review's verdict was "coverage is not the problem, authority is". This stage is that sentence
turned into edits. It is mostly deletion.*

#### W5 · One canonical `glossary.md` · ¾ d · needs W3

**Goal.** Replace **8 competing ubiquitous-language tables** with one.

**Read first.** `system-spec.md § Ubiquitous Language (Cross-Context)`; `domain-model.md`; the
`## Ubiquitous Language` section in 6 of 7 context overviews.

| ✓ | Step |
|---|---|
| ☑ | **First repair `system-spec.md`'s corrupted table at ~line 1103** — it breaks mid-cell into a duplicate OpenSearch field table, so the largest glossary being merged is itself incomplete. Mid-file, so no truncation marker helps; the glossary simply stops. |
| ☑ | Create `docs/spec/glossary.md`: term · definition · owning context · first introduced. Merge all 8 sources; where two disagree, the aggregate spec wins over the architecture tier. |
| ☑ | Add every term the 2026-08 corrections introduced that no glossary has: `EditSession`, `ReviewSession`, `OriginStatus`, `ConformanceGap`, `Alias`, `CompiledMetadataTemplate`, `SuppressedFieldNames`, `AllowsConcurrentEdit`, `VersionArtifact`, tier-policy, the saga state names, and `Job` / `Batch` / `Phase` / `Chunk`. |
| ☑ | Delete all 8 source sections. Context overviews link to the glossary; none defines terms. |
| ☑ | Do **not** put the glossary in the wiki. It is generated from `docs/`, lags it, and per `CLAUDE.md` should not be hand-edited — a glossary living downstream of the spec cannot be the spec's authority. |

**Done when.** `grep -rl 'Ubiquitous Language' docs/spec | grep -v glossary.md` returns nothing. If W2
has already landed, flip its context-overview rule from warn to fail; if not, W2 ships it as fail from
the start.

**Touches.** `glossary.md` (new), `system-spec.md`, `domain-model.md`, 6 × `context-overview.md`.

**Done 2026-08-25.** `docs/spec/glossary.md` — **68 terms**, one definition each, with an *Owner* column
(the context that gets to change the meaning) and an *Authority* column (the file to read when one line is
not enough). All eight sections deleted; each source file now carries a two-line pointer instead. W2's
`forbidden-section` rule **flipped `warn` → `fail`** and verified biting: a context overview that grows a
`## Ubiquitous Language` section back now fails CI. The section-check warning count dropped 128 → 122 and
**W5 is off the backlog entirely**.

**Column deviation, deliberate.** The step asked for *first introduced*; that date is unknowable for most
terms and unverifiable for the rest, so the fourth column is **Authority** — the file that owns the detail.
A pointer a reader can follow beats a date nobody can check.

**Part of the corrupted tail was recoverable, contrary to first appearances.** A full-blob search of
`Media.wiki` (the W0 §9.4 method) found the complete `Capability` row and **four rows the corruption had
swallowed** in blob `ba5debc2` (2026-04-23): **Event Store**, **Integration Event**, **Projection** and
**Saga**. Three of those four existed in **no other glossary in the tree** — they would have been lost
silently in a merge of the seven surviving sources. *(A first search for the completed sentence reported
zero hits; searching every blob rather than every revision found it. §9.4's point again.)*

**Nine substantive conflicts were resolved, not smoothed over.** The two that would have produced wrong
code:

- **`Standalone upload`** — AssetManagement's glossary said "full pipeline runs by default". `domain-model.md`
  retired exactly that rule by name (S12): a standalone asset is validated then **fast-exits to `Active`
  unprocessed**, and quota is **deferred to assign time, not exempted**. Four files side against the
  glossary. The retired rule is gone.
- **`DocumentSigningSaga`** — DocumentSigning's overview described it in the present tense as
  orchestrating live behaviour. The class does not exist. Marked ⚠ specified-not-built, as are all seven
  DocumentSigning terms. *(That file is the only context overview with no correction note anywhere — treat
  the rest of it as pre-correction too.)*

Also corrected: **`Validation`** did not name the right trigger — it happens asynchronously in Processing
via `AssetValidationWorker`, not on `ConfirmAssetUpload`, which multipart uploads never call at all.
**`Version (MediaItem)`** cited `ApproveMediaItem`, a command belonging to the never-built review saga; it
is `ApproveReviewCommand`. **`Capability`** claimed a MediaItem "never stores capabilities" while
`mediaitem.write-model.md` pins an immutable `MediaProfileSnapshot.Capabilities` at creation — both are
true of different things, and the glossary now says which. **`Document …`** was four spellings covering
**two different referents** (an item and an asset) with three incompatible storage claims; it is now two
entries, and the `tier-policy` rule is stated once: *not* tagged `managed` ⟹ stays in Standard, whether
untagged or tagged `retain`.

**Three terms are deliberately overloaded and say so:** `Alias` (RecordType vs OpenSearch index),
`OriginStatus` (on a ReviewSession vs on an EditSession — both real, different meanings), and `Processing`
(pipeline vs capability vs module). Silently picking one sense would have been worse than the duplication.

**Two things this unit did not settle, correctly:**

- **`AssetIngestionSaga`'s creation trigger is specified three ways** across `Processing/context-overview.md`,
  `system-architecture.md` and `asset.scenarios.md`, and its terminal state two ways (`Complete` vs
  `Completed`). The glossary states the `system-architecture.md` version and points at
  **[`open-questions.md#g-5`](#)** rather than inventing a resolution — a glossary is not the place to
  settle a saga's state machine.
- **`ChangeRequests` never had a glossary section**, which is why `MediaChangeRequest` had no home. Its
  entry is written from `ChangeRequests/context-overview.md`, including the CR-16 fact that **two change
  requests can be live on one MediaItem at once**, discriminated by `kind`.

**G-1 closed and deleted** from `open-questions.md` per that file's own rule; a short note records the
closure and preserves the `#g-2`…`#g-6` numbering so existing links keep working. `README.md` row 1 now
points at a file that exists.

---

#### W6 · Reconcile the architecture tier — 3 files, 3 answers · 1½ d · needs W3 · **D1**

**Goal.** "Which context owns what" and "what are the hosts" each have three answers. The architecture
tier is the one part of the spec that never had the 2026-08 correction pass, and it is what a new reader
opens first.

**Read first.** `architecture/bounded-context.md` (2026-03-11); `architecture/service-boundaries.md`
(2026-08-24, and it explicitly repudiates the first); `architecture/system-architecture.md` (705 lines);
drift-review X-1.1.

| ✓ | Step |
|---|---|
| ☑ | Merge into `architecture/bounded-contexts.md`, `service-boundaries.md` as the base — it is five months newer, and its topology is the one that was built. |
| ☑ | 🎨 **Carry over all four mermaid diagram sets.** `bounded-context.md`'s **Bounded Context Map**, Transport Topology, Saga Event Flows and Queue Topology were redrawn as mermaid on 2026-08-25 and **corrected against `src/hosts/` and the CDK** (X-4.14). They are the only accurate topology diagrams in the tree — `system-architecture.md`'s equivalents still carry the old wiring. **Do not regenerate them from the older file's ASCII.** Keep the 🟢/🟡/⛔ saga badges; they are what stops a reader building from `MediaItemReviewSaga`. The context map's edge labels carry the **relationship types**, which W3 established this file solely owns. |
| ☑ | **The aggregate inventory is already gone from the context map** — removed 2026-08-25 with a note pointing at `domain-model.md`. One of the three competing inventories is therefore closed; W7 still reconciles the remaining 9-vs-10-vs-12 between `domain-model.md` and the seven context overviews. |
| ☑ | ⚠️ **`## Internal Services` and `### Per-Service Event Contracts` are the last homes of the fictional topology** and were *not* rewritten in the diagram pass — only banner-flagged. They still name *Ingest API*, *Command Handler* and *SecuredSigning Adapter* as deployables across ~20 references. **These two sections are the merge's real work**, not the diagrams. |
| ☑ | ⚠️ **`bounded-context.md` looks like it was skipped by the 2026-08-24 correction pass** — 2 correction notes against `system-architecture.md`'s 7, while sitting on the losing side of five register entries (`open-questions.md` Q-1, Q-3, Q-5, Q-8, Q-14). Treat every claim in it as unverified during the merge, including the ones that look like they survived. |
| ☑ | ⚠️ **Correct two claims this unit inherited from the review, verified wrong 2026-08-25 (W3).** (a) `service-boundaries.md` does **not** repudiate `bounded-context.md` — it repudiates *its own* 2026-03-11 predecessor (`_Rewritten 2026-08-24 (drift review X-1.6)_`). (b) `service-boundaries.md:27` **explicitly delegates** bounded-context relationships and the context map *to* `bounded-context.md`. So the older file is stale on topology but is the **sole owner** of `### Context Relationship Types` — the only relationship-type table in the tree. **Carry that table into the merge; do not discard it as "the stale file's duplicate".** |
| ☑ | **Repoint `spec/README.md` rows 2, 3 and 10** at the merged file, and remove the `bounded-context.md` mentions from their *Not* columns. W3 deliberately pointed them at the files that exist today — a map is only useful if its rows are true on the day they are read. *(Row 3's Read target is `domain-model.md`, which is **W7's**, not this merge's — only its Not column changes here.)* Merging two files and forgetting the map is the easy mistake. |
| ☑ | **Do not carry over** `bounded-context.md`'s duplicate aggregate inventory, event catalogue, queue table or host list. Three inventories disagreeing 9 / 10 / 12 is two too many; the host list is stale per X-1.1. The aggregate inventory's single home is `domain-model.md` (W7). |
| ☑ | Assign a **relationship type to all 12 context relationships**, not just the 5 external ones. The 7 internal contexts appear in `system-spec.md` with no shared-kernel / conformist / partnership / ACL designation at all. |
| ☑ | Absorb `system-spec.md § Cross-Context Relationships` here (W8 will expect it gone from there). |
| ☑ | **`system-architecture.md` is the third answer, and no other unit touches it.** Its `## Services` section enumerates **twelve** numbered services — `### 1. Ingest API` … `### 12. Storage tier` (`:80`–`:401`) — against the nine real hosts. That is where the "8 vs 9 vs 12" of X-1.1 comes from. Reconcile it against `src/hosts/` and `service-boundaries.md`, or delete the section and link. |
| ☑ | Note that `### 6. SecuredSigning Adapter` and both Bulk workers are specified-not-built — `service-boundaries.md` already says so for SecuredSigning; BI-1 says so for the Bulk workers. |
| ☑ | Delete the dangling `specs/media-management-domain-spec.md` reference at `bounded-context.md:598` **before** deleting the file — **that file has never existed**, and `domain-model.md` cites it as the authority. (W7 removes the twin reference in `domain-model.md`'s header.) |
| ☑ | Delete **both** source files. Sweep inbound links for **both** names — `grep -rl bounded-context.md docs/` **and** `grep -rl service-boundaries.md docs/`. The merge deletes `service-boundaries.md` too, and both W25 and the drift review link to it; sweeping only the obvious one leaves half the links dangling. |

**Done when.** One file answers context ownership, one answers what the hosts are, every relationship has
a type, and no link points at either deleted file.

**Touches.** `architecture/bounded-contexts.md` (new), `bounded-context.md` and `service-boundaries.md`
(both deleted), `architecture/system-architecture.md`, `system-spec.md`, inbound links.

---

#### W7 · `domain-model.md` — inventory, relationships, the rules · 1 d · needs W6

**Goal.** Give the cross-*aggregate* dimensions the home they have never had.

**Read first.** `architecture/domain-model.md` (2026-04-26); `adrs/catalog-domain-invariants.md`;
drift-review X-9.6.

| ✓ | Step |
|---|---|
| ☑ | **The single aggregate inventory** lives here. Reconcile the 9 / 10 / 12 disagreement against `src/modules/` and state the count with its source. |
| ☑ | **Cross-aggregate relationship model** — currently nowhere. Which aggregate references which, and in which direction. |
| ☑ | **State the reference-by-id rule once, explicitly.** It is implied everywhere and stated nowhere. |
| ☑ | **State the one-aggregate-per-transaction rule** — and justify the one genuine exception (event append + name reservation), which is described but never defended. See X-9.6, which found the same seam from the code side. |
| ☑ | **Name the entity-vs-VO rule.** Applying it is W28; here just state the test. |
| ☑ | Absorb `system-spec.md § Naming Conventions` (W8 expects it gone). |
| ☑ | Delete the dangling `specs/media-management-domain-spec.md` reference from this file's own header at `domain-model.md:5` — **that file has never existed**, and this file cites it as its authority. (W6 removes the twin reference at `bounded-context.md:598` before deleting that file.) |

**Done when.** A reader can answer "how do these aggregates relate, and what may a transaction touch"
from one file.

**Touches.** `architecture/domain-model.md`, `system-spec.md`.

---

#### W8 · Split `system-spec.md` · 1 d · needs W5, W6, W7

**Goal.** 1,222 lines, 19 top-level sections, truncated twice — **its size is the truncation cause.** A
wholesale rewrite runs out of output budget in the same neighbourhood every time.

**Read first.** `shared/system-spec.md § Table of Contents`;
`reviews/spec-structure/…-2026-08-25.md § 7`.

| ✓ | Step |
|---|---|
| ☑ | Multi-Tenancy · Authentication & Authorization → `shared/multi-tenancy-and-auth.md` |
| ☑ | Concurrency · Idempotency · Cross-Aggregate Constraint Enforcement → `shared/concurrency-and-consistency.md` |
| ☑ | Event Sourcing Mechanics · Messaging Patterns · Storage Boundaries · S3 Upload Patterns → `shared/event-store-and-messaging.md`. **Not `persistence-and-eventing.md`** — `docs/adrs/persistence-and-eventing.md` already exists, and two files one directory apart sharing a basename is how the wrong one gets opened. Check the other four names against `docs/adrs/` before creating them. |
| ☑ | Saga Coordination Patterns → `shared/saga-patterns.md` — the cross-cutting rules only; individual sagas get their own files in W19. |
| ☑ | Infrastructure · Observability · **Disaster Recovery** · CORS · Rate Limiting → `shared/operations.md`. **The DR section is the one still truncated** — move what survives; W14 completes it in its new home. |
| ☑ | Cross-Context Relationships → already moved by W6. Ubiquitous Language → already moved by W5. Naming Conventions → already moved by W7. Verify all three are gone rather than duplicated. |
| ☑ | **Delete `system-spec.md`.** Do not leave a stub — a file that survives as a stub is one somebody writes into again. Update every inbound link; there are many. |
| ☑ | Carry the `⚠ TRUNCATED` marker into `shared/operations.md` with the DR section, so W14's target is still marked. |

**Done when.** `system-spec.md` does not exist, no link points at it, and all 19 sections are findable
from `spec/README.md` — 15 in the five new `shared/` files, 3 already relocated by W5/W6/W7, and the
Table of Contents discarded.

**Touches.** 5 new `shared/` files, `system-spec.md` (deleted), inbound links across `docs/`.

---

#### W9 · `_Last reviewed:` + kill dangling references · ½ d · needs W2, W8

| ✓ | Step |
|---|---|
| ☑ | Add `_Last reviewed: YYYY-MM-DD_` to every spec file. Undated files are why nobody can tell which side of the drift review a claim sits on — 5 carry no date header at all, including `api-conventions.md` and `security-scenarios.md`. |
| ☑ | Use the file's last substantive edit date, not today's, or the line means nothing. |
| ☑ | Sweep for links to files deleted in W5–W8 and to `specs/media-management-domain-spec.md`. |
| ☑ | **Start from W3's sweep, don't re-derive it.** A full relative-link scan of `docs/` on 2026-08-25 found **3** dangling links **outside `_recovered/`**: `adrs/README.md → ./deployment-and-resource-naming.md` (**never existed in any revision** — the ADR index promises a topic document nobody wrote; decide whether to write it or drop the row), `adrs/archive/ADR-010… → ../../../repos/magiq-media/media-profile-conformance-plan.md`, and `breaking-changes/breaking-changes.md → ../../RUNBOOK.md`. **Exclude `docs/spec/_recovered/`, which holds 12 more by design** — quarantined salvage, untracked in git, deleted at W18; its own README says to exclude it from link checks. Re-run the scan after W5–W8, which create most of the breakage this step exists for. |
| ☑ | Flip W2's `_Last reviewed:` check from warn to fail. *(This is why W9 is blocked on W2 as well as W8.)* |

**Done when.** W2 is fully failing-strict and green.

**Touches.** all of `docs/spec/`.

---

#### W10 · Sweep within-file contradictions (Tier 3) · ½ d · needs W4, W8

**Goal.** The contradictions a merge or a banner does not reach — two claims inside one file.

| ✓ | Step |
|---|---|
| ☑ | `MediaItemStatus` membership. |
| ☑ | `ITenanted` vs `ITenantScoped` — spec side only; the platform SDK defines `ITenantScoped`. |
| ☑ | Projector count · bucket count. |
| ☑ | `FailureCategory` wire values that would throw on `Enum.Parse`. |
| ☑ | Anything unresolvable in one sitting → `open-questions.md` (W4), not a TODO comment. |
| ☑ | **`MediaItemStatus` membership is partly done** — `mediaitem.read-model.md`'s enum was corrected against `MediaItemStatus.cs` on 2026-08-25 (W1) with its source cited. The rest of the tree is still this unit's. |

**Done when.** Every Tier-3 contradiction in the DDD review's §5 is resolved or registered in
`open-questions.md`. *(Tier 1 is not this unit's — those are W4, W11, W12, W22 and W23.)*

**Touches.** various.

---

#### W11 · Integration event naming — decide, delete, ADR · ½ d · needs W4 · **D3**

| ✓ | Step |
|---|---|
| ☑ | Read the `*IntegrationEventPublisher` classes for what is **actually published**. Code decides; the spec does not get a vote. |
| ☑ | Delete the losing scheme from every spec file. **Do not alias** — external SNS filter policies cannot be written against both. |
| ☑ | Write the ADR. |
| ☑ | Close the entry in `open-questions.md`. |

**Touches.** spec files carrying either scheme, `docs/adrs/`, `docs/spec/open-questions.md`.

---

#### W12 · Read-model table names against the CDK · ¼ d · needs W4, W8

| ✓ | Step |
|---|---|
| ☑ | `media-*-detail` vs `media-*` — resolve against `cdk-magiq-media`, the only physical truth. `system-spec.md` contradicts itself here: `:674` is under *Storage Boundaries* and `:990` under *Infrastructure Overview*, so after W8 the two halves live in **different files** — `shared/event-store-and-messaging.md` and `shared/operations.md`. Fix both. |
| ☑ | Close the entry in `open-questions.md`. |

**Touches.** `shared/event-store-and-messaging.md` (`:674`), `shared/operations.md` (`:990`), `<agg>.read-model.md` files.

---

### Stage C · Retire the salvage

*Three tails were recovered from history but quarantined because they predate the 2026-08-24 correction
pass; two were never recoverable. Each unit is one file. Full provenance in §9.*

> **Prior for a quarantined tail: assume it is wrong.** It was written before the correction pass on the
> file it belongs to. Reconcile, don't proofread.

#### W13 · DDD-T11 · RecordType uniqueness contract · ½ d · needs nothing

**Read first.** `docs/spec/_recovered/recordtype.write-model.DDD-T11.md` (3,683 B, written
**2026-04-23**); `src/modules/Metadata/Metadata.WriteModel`.

| ✓ | Step |
|---|---|
| ☑ | Rewrite the transaction and conflict-handling prose: the source describes a MediatR `TransactionBehavior` and `NameReservationConflictBehavior`; **this repo dispatches via `ICommandDispatcher` and does not use MediatR**. |
| ☑ | Confirm — do not assume — the `IRecordTypeUnicityService` body, the `RECORDTYPE` scope key, and the per-operation reservation intents (`Reserve` / `Swap` / `Release`). These are the parts most likely to have survived four months intact, which is exactly why they need checking. |
| ☑ | Check the Published / Consumed Integration Events tables against the actual publisher. |
| ☑ | Move the corrected text into `recordtype.write-model.md`, delete its `⚠ TRUNCATED` marker, delete the `_recovered/` file. |

**Done 2026-08-25.** The section is rewritten from `Metadata.WriteModel` and the platform SDK,
the marker is gone, and `_recovered/recordtype.write-model.DDD-T11.md` is deleted — **three
`⚠ TRUNCATED` markers remain** (T10, T12, T16/T17) and `_recovered/` is down to two files plus its README.

**The step that mattered was the one that said "confirm, do not assume".** It named three things "most
likely to have survived four months intact." **All three were wrong**, and so was everything around them:

| The recovered text said | Reality |
|---|---|
| `IRecordTypeUnicityService`, module-local, with `NameExistsAsync` | **No such interface exists in `src/`.** Names go through the platform's `INameReservationService`, the same service as aliases |
| Scope key `RECORDTYPE` | `record-types` (`ScopeKeys.RecordTypes`); aliases use `record-type-aliases` |
| `NameExistsAsync` returns `true` when taken | The method is `IsNameAvailableAsync` and `true` means **free** — the polarity is inverted |
| Reservation and save commit atomically via an ambient `ITransactionScope` | **No transaction.** Reserve happens *before* `SaveAsync`, and nothing spans them (X-9.6) |
| Conflicts handled by a `NameReservationConflictBehavior`; "handlers never catch it directly" | Handlers **catch `NameReservationConflictException` explicitly** and map it to `RecordTypeNameConflict`. The exact inverse |
| Events named `RecordTypePublishedMessage` / `RecordTypeDeprecatedMessage` | `*IntegrationEvent`; the `Message` suffix was never used here |
| Published by `RecordTypeIntegrationEventPublisher` | `RecordTypeDomainEventMapper`, an `IDomainEventMapper<T>` (X-3.3) |

**One claim survived: the table name, `media-name-reservations`.** That is the entire yield of four
months-old prose, and it is worth remembering the next time a quarantined tail looks plausible. Stage C's
prior — *assume it is wrong; reconcile, don't proofread* — was not cautious enough here; the text was not
drifted, it described a design this repo has never shipped.

**Both missing integration-event sections were written, closing 2 of W30's 17 unowned findings.** W2 had
flagged `recordtype.write-model.md` as lacking *Published Integration Events* and *Consumed Integration
Events*; both now exist and are verified. Consumed is genuinely **none** — Metadata has no
`IntegrationEvents/Consuming` folder and no `IIntegrationEventHandler<T>` anywhere.

> 🚨 **The code check found a live production bug — raised as X-4.16 (High).**
> `media.recordtype.published` and `media.recordtype.deprecated` are **not on the
> `media-cross-module-events` filter allowlist**. The allowlist's `// Metadata (RecordType)` comment sits
> above `media.profile.published` / `media.profile.deprecated`, which are **MediaProfile** events. So both
> RecordType events are published to SNS and filtered out before delivery, while `ConsumerRegistrations`
> registers handlers for them and Catalog implements three consumers that **can never run**. Catalog's
> RecordType version reference model is therefore never maintained: **a deprecated RecordType is never
> marked deprecated, so `MediaProfile` will keep accepting pins to it.** Silent — no error, no DLQ, no
> alarm. Two-line fix in `sqs-queues.ts`, but expect a backlog when it starts flowing.
>
> **This is X-4.15 landing within a day of being raised.** X-4.15 said the two SNS allowlists are
> hand-maintained mirrors of C# registration methods with nothing enforcing the mirror, and cited CR-21 as
> the precedent. X-4.16 is the second instance, and it was found by reading one aggregate's spec. **The
> build-time check X-4.15 proposes should be treated as due, not nice-to-have** — there are likely more.

---

#### W14 · DDD-T16 · DR runbooks · ½ d · needs W8

**Read first.** `docs/spec/_recovered/system-spec.DDD-T16.md` (3,299 B, written 2026-06-13);
`cdk-magiq-media`; drift-review X-1.1.

| ✓ | Step |
|---|---|
| ☑ | Re-map five phantom Lambdas — `Media.Api`, `Media.QueryApi`, `Media.Projectors.Lambda`, `Media.SagaOrchestrator.Lambda`, `Media.Processing.Lambda`, **none of which exist** — to the real hosts: `Api`, `QueryApi`, `Projectors.ReadModel`, `Projectors.Search`, `EventConsumers`, `ProcessingWorker`, `SagaOrchestrator`, `TimeoutScanner`. `cdk-magiq-media` is authoritative for deployed function names and aliases. |
| ☑ | The Backup Verification Schedule table is **cut mid-cell in the source too** — the only recovery that came back incomplete. Finish it from the CDK, or cut it. |
| ☑ | Write into `shared/operations.md` (W8's destination), not into the deleted `system-spec.md`. |
| ☑ | Delete the marker and the `_recovered/` file. |

---

#### W15 · DDD-T10 · MediaItem asset subscriptions · ¼ d · needs nothing

**Read first.** `docs/spec/_recovered/mediaitem.write-model.DDD-T10.md` (1,124 B, 2026-07-16 — the
freshest of the three); AssetManagement domain events.

| ✓ | Step |
|---|---|
| ☑ | One name, two answers: the tail says `AssetUploaded`; the surviving text above the cut attributes the same fields to `AssetUploadInitiated`. AssetManagement's events are the arbiter. |
| ☑ | Decide whether the `media-change-requests` reference-model section — present in wiki blob `ba9bce72`, **deliberately never restored** — belongs in this file. If yes it needs `Resolved` / `Abandoned`, not `Approved` / `Rejected`. Overlaps W20. |
| ☑ | Move in, delete marker, delete `_recovered/` file. |

**Done 2026-08-25.** Marker gone, `_recovered/mediaitem.write-model.DDD-T10.md` deleted — **two markers
left** (T12, T17) and `_recovered/` is down to `system-spec.DDD-T16.md` plus its README.

**The event-name question resolved as expected — `AssetUploaded` has never existed.** The events are
`AssetUploadInitiated` and `AssetUploadConfirmed`; the surviving spec text was right and the recovered
tail was wrong. But checking that one name turned up **a bigger error in the text that survived**:

> **The section was headed `media-assets` and described the data as "owned by AssetManagement".** That is
> AssetManagement's own read model. **Catalog does not read another context's read model** — it maintains
> its own reference index, **`media-catalog-asset-ref`**, projected from AssetManagement's *integration*
> events by `AssetReferenceIndexProjector`. As written, the spec described a boundary violation that the
> code does not commit. Corrected, along with the delivery path: the recovered text said
> `media-projector`, which carries raw domain events and is subscribed only by the two projector hosts —
> cross-module reference models are fed by `media-cross-module-events` → `EventConsumers`.

Field names were wrong too: **`SourceStorageKey` is `StorageKey`**, `Status` and `ContentType` are stored
as strings rather than the enum/value-object types the table claimed, and `TenantId` and `ProjectedVersion`
were missing entirely.

**The subscribed-event table was wrong in three directions at once** — it named an event that does not
exist (`AssetUploaded`), two the projector does not handle (`AssetValidationPassed`,
`AssetValidationFailed` — and there is **no `AssetValidationFailedIntegrationEvent` at all**, so nothing
outside AssetManagement can react to a failed scan), and **omitted `AssetInfectionDetected`**, the one
event that clears `StorageKey`. That omission matters: it is the compliance path behind
[`open-questions.md#q-4`](#), and the projector's own comment confirms the S3 object is hard-deleted.
`AssetDeleted` was listed as a status update; it deletes the row.

**The `media-change-requests` question answered yes — and found a live reference model specified
nowhere.** Catalog runs `ChangeRequestReferenceIndexProjector` maintaining
`media-catalog-change-request-ref`, read by `ChangeRequestQueryService` to answer *does this MediaItem
have an open change request?*. The spec had **no coverage of it whatsoever**. It is now documented, and
the plan's prediction held exactly: the wiki version was written against `Approved` / `Rejected`, and the
real events are **`ChangeRequestCreated` / `Resolved` / `Abandoned`**. Worth noting for **W20**: the index
stores a **boolean `IsOpen`, not a status**, so both closure paths collapse to one write — a caller
needing to know *why* a request closed cannot get it from here.

**Stage C's prior held again.** Of the recovered tail's two parts, the Related link list was age-immune
and restored as-is (plus links to the new `glossary.md` and `open-questions.md`); **every factual claim in
the event table was wrong.** Two salvage units in, the pattern is consistent: link lists survive, tables
naming code do not.

---

#### W16 · DDD-T12 · ProcessingJob mirror rules · ¼ d · needs nothing

**Target.** `docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md` — cut at
`Mirrors current job statu`. **Nothing survives to work from**; every revision in both repos cuts at the
same token.

| ✓ | Step |
|---|---|
| ☑ | Write the read-model mirror rules from the real projectors: `ProcessingJobDetailProjector`, `ProcessingJobSummaryProjector`. **There is no `ProcessingJobProjector`** — see X-11.1. |
| ☑ | Delete the `⚠ TRUNCATED` marker at the end of the file. |

**Done 2026-08-25.** Marker gone — **two markers left** (T16, T17), both of which W14 and W17 own.

**This unit's own step was aimed at the wrong section, and the mistake was informative.** It said to write
*read-model* mirror rules from `ProcessingJobDetailProjector` / `ProcessingJobSummaryProjector`. The cut
is not in a read-model section at all — it is in **`## Write-Side Reference Models` → `AssetProcessingJobIndex`**,
a write-side index maintained by **`AssetJobIndexProjector`**. The two read-model projectors are a
different concern and belong to `processingjob.read-model.md`; the section now says so explicitly, so the
conflation does not recur. *(The marker itself named a third class, `ProcessingJobProjector`, which does
not exist — X-11.1 again, and a reminder that the markers were written from the last surviving heading
rather than from code.)*

**The truncated sentence was about to state something false, and that is the finding.** It read
*"`Status` | `ProcessingJobStatus` | Mirrors current job statu…"*. It does not mirror:
`AssetJobIndexProjector` writes **`Status = Running` on both terminal events**, so a row never reaches
`Succeeded` or `Failed`. Once a job starts, its index row reads `Running` permanently.

**Nothing is broken today, and that is precisely why it is dangerous.** Both consumers use the index only
for the `AssetId → JobId` lookup it exists for — `AssetIngestionSaga` reads `job.JobId`, the timeout
scanner reads the key — and the `Status` the scanner filters on is the **saga's**, in `media-sagas`, a
different table entirely. `StartedAt` is written and never read either. So the field is a loaded gun with
a plausible name: the first consumer to reach for `index.Status` gets a wrong answer with no error.
Raised as **X-4.17 (Med)** with the recommendation to fix the two writes or delete the field — leaving it
as-is is the worst of the three options.

**Third salvage unit, third time the surviving text was worse than the lost text.** W13's tail yielded one
true claim; W15's yielded a link list; W16's tail was unrecoverable and turned out not to be worth
recovering — the sentence was wrong. The consistent value in Stage C has not been the recovered prose. It
has been that reconciling each tail forces someone to read the code around it.

---

#### W17 · DDD-T17 · `workflow_dispatch` docs · ¼ d · needs nothing

**Target.** `docs/spec/architecture/branching-and-deployment.md` — cut at `` `workflow_di ``. **Nothing
survives to work from**; the single prior revision cuts identically and the page was never published to
the wiki.

| ✓ | Step |
|---|---|
| ☑ | Write the manual-dispatch trigger documentation from `.github/workflows/build-and-push.yml`. |
| ☑ | Cross-check against `cdk-magiq-media` — the deploy trigger is a commit into that repo's `config/<env>.json`, not `repository_dispatch`. |
| ☑ | Delete the marker. |

**Done 2026-08-25. One `⚠ TRUNCATED` marker remains in the whole tree** — `shared/system-spec.md`
(DDD-T16), which W14 owns.

**The cross-check step earned its place: the step above aimed at one workflow and the cut needed two.**
The sentence broke inside a bullet about **cdk-magiq-media's** trigger — *"prod only deploys on a `v*`
tag … or a manual `workflow_di…"* — so writing it only from `build-and-push.yml` would have documented
the wrong dispatch. There are **two** `workflow_dispatch` entry points doing different jobs, and reaching
for the wrong one is the easy mistake: `build-and-push.yml` **produces** an artifact and hands off by
committing the tag; `cdk-magiq-media/deploy.yml` **deploys** one that already exists. Both are now
documented side by side, with their real inputs.

Three behaviours were worth writing down explicitly:

- **A gated dispatch is skipped, not failed.** `environment=prod` needs `PROD_ENABLED='true'` and
  `environment=staging` needs `STAGING_ENABLED='true'`; without them the job is skipped, so **a green tick
  on a dispatch you expected to reach prod can mean nothing happened.**
- **Staging has no config file.** `env=staging` resolves to `config/qa.json` and deploys whatever QA
  holds — deliberate, so staging validates exactly what QA proved. It also runs as a separate
  `deploy-staging` job.
- **A missing `imageTag` is a hard failure, not a default.** Nothing is inferred; the run stops and tells
  you to seed the config file.

> 🔒 **Surfaced into the spec: there is no platform-enforced approval gate on staging or prod.**
> `deploy.yml` binds `environment: staging` / `prod` for per-account roles, but **no required-reviewer
> protection is attached** — GitHub environment protection needs Team plan or above for private repos and
> this org is not on it (a 422 confirms). **"Tom approves" is a process convention, not something the
> platform blocks on**; anyone who can run the workflow can deploy. This was buried in a comment in
> `deploy.yml` and stated nowhere a reader of the spec would find it. The only real gate today is
> `PROD_ENABLED` / `STAGING_ENABLED` being left unset — a configuration switch, not an approval.

**Stage C's salvage units are finished** apart from W14, which is blocked on W8. `_recovered/` is down to
`system-spec.DDD-T16.md` and its README, so **W18 is one unit away.**

---

#### W18 · Delete `docs/spec/_recovered/` · 5 min · needs W1, W13–W17

| ✓ | Step |
|---|---|
| ☑ | Delete the folder, README included. |
| ☑ | Remove W1's `_recovered/` exclusion and W1's mid-construct allowlist — with all five markers gone, the guard should be unconditional. |

> A quarantine folder that outlives its quarantine becomes a second source of truth. This repo has
> already failed to delete `docs/implementation-plans/` and `BULK-IMPORT-SPEC-UPDATES.md`; do not make it
> three.

---

### Stage D · The domain risk

*Stages A–C make the spec trustworthy. **This stage is the one that answers "build a solid domain
model"** — it is where the spec is not merely contradictory but absent, on a live system.*

#### W19 · `sagas/` file type + `AssetIngestionSaga` · 1½ d · needs W3, W8

**Goal.** Sagas are the one genuinely missing dimension — **no owning file exists anywhere in the spec.**
`AssetIngestionSaga` is in production with 5 handlers under `src/hosts/SagaOrchestrator/AssetIngestion/`
and no spec at all.

**Read first.** `src/hosts/SagaOrchestrator/AssetIngestion/Handlers/*`; `SagaRegistrations.cs`;
`shared/saga-patterns.md` (from W8).

| ✓ | Step |
|---|---|
| ☑ | Establish the file type at `contexts/<Ctx>/sagas/<saganame>.md`. Owning context = the one that owns the **outcome**; `AssetIngestionSaga` → AssetManagement. Cross-context sagas get a link from each participating `context-overview.md`. |
| ☑ | Write `contexts/AssetManagement/sagas/assetingestionsaga.md` to W2's contract: `Purpose` · `Correlation Key` · `State Table` · `Transition Table` · `Timeouts` **with their config keys** (today the spec says only "Video = 4h, others shorter") · `Compensation` · `Idempotency` · `DLQ & Poison Policy` · `Manual Intervention Runbook`. **— filed in `contexts/Processing/`, not `AssetManagement/`; deviation and reasoning recorded in the file and the session log.** |
| ☑ | **Specify the bypass-branch exit.** A bypassed asset emits neither `ProcessingJobSucceeded` nor `ProcessingJobFailed` — the only two closure triggers listed — so the fast-exit branch **has no stated way to end**. This is a live behavioural hole, not a documentation gap: confirm against the handlers whether the saga actually terminates, and if it does not, that is a **code** finding, not a spec one. |
| ☑ | Cross-cutting, into `shared/saga-patterns.md`: correlation-id scheme, retry budget, DLQ policy, runbook conventions. |
| ☑ | Add the `sagas/` row to `spec/README.md`, marked live rather than planned. |

**Done when.** The production saga has a file, and the transition table has no row that cannot be reached
or exited.

---

#### W20 · Delete `MediaItemReviewSaga` from 4 files · ½ d · needs W6, W8, W19

**Goal.** A saga specified four ways that **does not exist**. *(D6 resolved: this plan owns it, not the
drift review.)*

| ✓ | Step |
|---|---|
| ☑ | Delete from `bounded-context.md:624` *(gone after W6 — verify it did not survive the merge)*, `domain-model.md:317-319`, `system-architecture.md:293,322,337`, `system-spec.md:885` *(→ wherever W8 put it)*. |
| ☑ | **`media-catalog-change-request-ref` is a boolean, not a status** *(documented 2026-08-25 by W15)*. `ChangeRequestReferenceIndexProjector` stores `IsOpen` and collapses `Resolved` and `Abandoned` into the same write. Any spec text implying Catalog can tell *why* a change request closed from this index is wrong — it must load the aggregate. |
| ☑ | `ChangeRequests/context-overview.md` (2026-08-23) is the reconciled version: **the direction is inverted.** Catalog emits `MediaItemApprovedIntegrationEvent`; ChangeRequests' own handler dispatches `ResolveChangeRequestCommand`. No saga. |
| ☑ | `system-spec.md:885` additionally specified it over `ChangeRequestApproved` / `ChangeRequestRejected` — **events the write model does not have.** It has `Resolved` / `Abandoned`. Fix wherever else those names appear. |

---

#### W21 · `DocumentSigningSaga` + the two fan-out workers · 1 d · needs W19

| ✓ | Step |
|---|---|
| ☑ | `DocumentSigningSaga` — spec as **design, not as shipped**: the code is deferred, `DocumentSigning` has no `.Endpoints` project, and nothing deploys `SagaOrchestrator.DocumentSigning`. Say so in the file. |
| ☑ | Give it the correlation key it has never had — the spec offers `SigningSessionId`, `MediaItemId` and `EnvelopeId`. One timeout value instead of three, with its config key. |
| ☑ | **The two process managers nobody calls sagas:** `CollectionArchiveFanOutWorker` and `IFolderArchiveFanOutWorker` have no failure, retry, partial-completion or resume spec. **A half-archived subtree currently has no compensation and no status surface.** Spec both to the same contract. |
| ☑ | If a fan-out worker turns out to have no resume path in code, that is a code finding — file it. |

---

#### W22 · Authorization matrix — privileged subset first · 2 d · needs W8 · **D5**

**Goal.** `system-spec.md § Command-Level Authorization` covers **6 of ~150 commands**. For a government
platform, the unlisted privileged ones are the risk.

| ✓ | Step |
|---|---|
| ☑ | Rebuild **from code** — endpoint attributes plus handler guards. Not from the spec. |
| ☑ | Privileged first: `ForceReleaseCheckout`, `ExpireCheckout`, every `actor.ActorType == "System"` path, every Processing and Bulk command. All currently unlisted. |
| ☑ | Then the long tail, or enumerate and date what is left. |
| ☑ | Resolve **Approve authorization**, specified three ways — reviewer-scoped / System-only / `ReviewSession` roster — across `system-spec.md:147` *(→ `shared/multi-tenancy-and-auth.md` after W8)*, `security-scenarios.md:123`, `error-catalog.md:297`. |
| ☑ | Resolve **MediaProfile listing**: `mediaprofile.api.md:41` documents an owner-scoped check on `caller.owner_id`; `mediaprofile.read-model.md:223` says that query never existed and **every profile in the tenant is returned to every caller**. Confirm against code, then fix whichever side is wrong. |
| ☑ | **Anything the code does not enforce stops being a spec task** — it becomes a security finding with its own urgency. Escalate immediately rather than filing it. |

---

#### W23 · MediaItem's three state machines, one table · 1½ d · needs W2 · **D4**

**Goal.** Status × edit-session/checkout × folder-assignment. Each machine is specified alone; their
interaction is defined nowhere. One table closes a dozen open questions at once.

| ✓ | Step |
|---|---|
| ☑ | Add the interaction matrix to `mediaitem.write-model.md` under the `State Machine Interaction` heading W2 expects. |
| ☑ | Answer explicitly, in that table: does `Archive` close an open `EditSession`? What raises `EditSessionCloseReason.Submitted` — the value exists and no method sets it? Can a non-editor `Publish` / `Archive` / `Withdraw` an item another user holds? Is `Withdraw` / `Archive` legal from `Revising` — the diagram has the arrow, the methods do not list the state? |
| ☑ | **Document** the `Capability` enum in `mediaprofile.write-model.md` — there is nothing to *fix*. Verified 2026-08-25: one enum, nine values, same type on the endpoint and the command, no restricted list anywhere, defaults all valid. The three-way conflict D4 was raised for does not exist in code. It is still the pivot of the activation chain and still specified nowhere, so it needs a home; write it from the enum. |
| ☑ | Resolve asset status on role assignment — "any status" vs "must be `Active`". |
| ☑ | Resolve the write/read seam: `AcceptedContentTypes` is written, `AllowedMediaCategories` is read. Clients hit this directly. |

---

#### W24 · Cross-aggregate invariants + cascade rules · 1 d · needs W7

| ✓ | Step |
|---|---|
| ☑ | `shared/cross-aggregate-invariants.md` — one catalogue. E.g. "a Registration's MediaItem must be Published"; "a Folder cannot be archived with active registrations in its subtree". These currently live in `adrs/catalog-domain-invariants.md`, **outside the spec tree, in a folder for decisions rather than rules**. |
| ☑ | Leave the ADR in place as the decision record it is; move the *rules* out of it and link back. |
| ☑ | `shared/cascade-rules.md` — one table. Today `domain-model.md` says "archiving is read-layer only — no write-side cascade" while `bounded-context.md` *(→ merged into `architecture/bounded-contexts.md` by W6)* describes a fan-out job that archives the whole subtree. Check what survived the merge before assuming the contradiction is still live. |
| ☑ | Undefined everywhere, decide each: what happens to **Assets** when a MediaItem is archived; to **Registrations** when a Folder is archived; to **MediaItems** when a MediaProfile is deprecated. |

---

### Stage E · Consolidate

#### W25 · `shared/consistency-model.md` · ½ d · needs W6

**Goal.** Projection *mechanics* are well documented. **Policy does not exist.**

| ✓ | Step |
|---|---|
| ☑ | Create `shared/consistency-model.md`: read-your-own-writes rule; projection-lag bound or SLO — `api-conventions.md` alludes to "a client that reads a lagging projection" and gives **no figure**; rebuild procedure. |
| ☑ | Cover the reference indexes that **cannot be rebuilt by aggregate replay** — stated at `service-boundaries.md:133` *(→ `architecture/bounded-contexts.md` after W6)*. That is the case where the policy actually bites. |
| ☑ | Add the `Consistency` section W2 requires to each `<agg>.read-model.md`: lag class + RYOW behaviour, linking here. |

---

#### W26 · The three missing `scenarios.md` · 1 d · needs nothing

| ✓ | Step |
|---|---|
| ☑ | `Folder/folder.scenarios.md` — **does not exist and never has** *(history-checked 2026-08-25: no blob in either repo at any revision; genuinely greenfield)*. Folder's two highest-risk behaviours — archive cascade and cross-collection subtree move — have **no worked example anywhere**. |
| ☑ | Add the Folder-owned scenarios to `Catalog/business-scenarios.md` so the hole is visible if it reopens. |
| ☑ | Both Bulk import scenarios — coordinate with drift-review BI-1/BI-2 rather than duplicating. `BulkMediaImportWorker` is a five-phase process manager across three modules, spec'd with no compensation, no timeout and no dedup rule. Mark them intent, per the code check. |

**Done 2026-08-25.** All three files written; **W26 is off the backlog entirely** and its rule is
**flipped `warn` → `fail`**, verified biting — an aggregate that loses its `scenarios.md` now fails CI.
Section warnings 120 → 119. Indexed in `Catalog/business-scenarios.md` with the bulk entries marked
⚠ intent. Scenario ids are `FLD-n` rather than `F-n`, to avoid colliding with the `F-n` drift-review
finding ids that `folder.write-model.md` cites.

**`folder.scenarios.md` was written from code, and the code disagrees with the aggregate's own comments in
three places.** Worth knowing before W20 or any Folder work:

- **The archive cascade is write-side and fully synchronous** — `ArchiveFolderHandler` awaits
  `FolderArchiveFanOutWorker` inside the HTTP request, dispatching real `ArchiveFolderCommand` /
  `ArchiveMediaItemCommand` per node. `Folder.cs`'s comment above `Archive` says a projector fans out
  `isAccessible = false` via a `FolderItemsIndex` GSI. **No such GSI, no such projector, no such
  behaviour.** `Collection.cs` carries the identical false comment. *The spec file has this right; the
  code comments are the wrong side* — the reverse of the usual direction, and worth remembering.
- **`FolderHasActiveChildren` does not exist** (the comment claims it blocks archive), and the
  registration check the same comment calls a "non-blocking warning" is **blocking**, returning 422.
- **There is no resume path, and failures are swallowed.** Descendant failures are logged as warnings, so
  **the target folder archives even if every descendant failed, and the caller still gets `204`.** A
  thrown exception leaves an arbitrary prefix of the subtree archived and durably committed with nothing
  to roll back to. Partial completion is not observable anywhere.
- **Recursive re-entry means a *successful* archive logs a burst of "Failed to archive…" warnings** —
  each dispatched command re-runs the whole cascade for its own subtree, hitting already-archived
  aggregates. Work is `O(Σ subtree sizes)`. Anyone reading these logs will otherwise think the operation
  failed.

**The cross-collection move gap is worse than `folder.write-model.md` states**, and that file is corrected
to match: it describes descendants' *read-model rows* keeping the old `CollectionId` "until they are
rebuilt". In fact the **descendant `Folder` and `MediaItem` aggregates hold the stale value**, so **a
projection rebuild reproduces it rather than repairing it.** Because the hierarchy GSI is keyed on
`CollectionId`, the moved folder appears in the destination collection while **its entire subtree still
appears in the source collection**. Descendant depth counters are never adjusted either, so the 10-level
limit keeps being enforced against pre-move depth indefinitely.

**The bulk files are marked intent throughout and deliberately document what is missing rather than
inventing it.** Each is three scenarios: the happy path, and the two questions the design does not
answer — **no compensation** at any phase boundary and **no dedup rule**, plus **no timeout** on
`BulkMediaImportJob`'s `AwaitingUploads`, which waits on a third-party client whose pre-signed URLs expire
in 15 minutes. `BulkMediaImportJob` is a five-phase process manager across three modules; the file says
plainly that it is a saga in all but name and should inherit G-5's contract if it is ever built.

**Both bulk files warn on `Diagram Key` (owned by BI-1) and that is correct** — there is no behaviour to
diagram. Filling in the heading to satisfy the checker would be exactly the anti-pattern the check exists
to prevent.

---

#### W27 · Retire `BULK-IMPORT-SPEC-UPDATES.md` · ½ d · needs W11

| ✓ | Step |
|---|---|
| ☑ | Merge out `BulkCreateMediaItemsCommand` and the SQS/DLQ configuration — **they exist nowhere else.** |
| ☑ | **Delete the file.** It is an unmerged changelog in imperative future tense sitting in `aggregates/`, and it prescribes `/v1/catalog/...` routes — confirmed 2026-08-25 that **no route in the codebase carries a `catalog` segment**. |
| ☑ | Same sweep for any other `/v1/catalog/...` left in the spec. |

---

#### W28 · Apply the entity-vs-VO rule · ½ d · needs W7

| ✓ | Step |
|---|---|
| ☑ | Apply W7's rule: `Reviewer`, `ReviewComment`, `RegistrationItem`, `RegistrationAmendment` and `Signer` all have identity and mutable state but are catalogued as value objects. |
| ☑ | `Folder` **and `Collection`** have **no `Value Objects` section at all** — W2 warns on both. *(Corrected 2026-08-25: this step named only Folder. The other five write-models W2 first reported are false gaps — they give each value object its own `## <Name> Value Object` section, which the check now matches.)* |

---

#### W29 · Tier 2 client-contract sweep · 1 d · needs W12

| ✓ | Step |
|---|---|
| ☑ | Status codes · route spellings · part-URL TTL · bulk batch caps · download authorization · delete semantics. |
| ☑ | Idempotency: the spec claims it exists — **this plan owns that claim**; drift-review X-10.5 owns the OpenAPI half. Coordinate, note in both. |

---

#### W30 · Close the 19 unowned section gaps + 35 renames · 1½ d · needs W2

**Goal.** W2 measured the tree against the file-type contracts and found 19 missing sections that **no
other unit on this board would ever fix** — they are not glossary, not consistency, not authorization, not
scenarios. Plus a 35-item heading-rename backlog. This unit exists so W2's check can eventually go green
instead of warning forever.

**Read first.** `python3 .github/scripts/check-spec-sections.py --root docs/spec` — the live list, with an
owner against every line. Anything marked `[unowned]` is this unit's. Do not work from the snapshot below;
work from the run.

| ✓ | Step |
|---|---|
| ☑ | **The 19 gaps, concentrated in 5 files.** `mediachangerequest.write-model.md` (3: `Properties`, `Status transitions`, `Consumed Integration Events`) · `Processing/context-overview.md` (3) · `processingjob.api.md` (3: `API Conventions`, `Write Endpoints`, `Read Endpoints`) · `recordtype.write-model.md` (2) · `ChangeRequests/context-overview.md` (2). The remaining 6 are singletons. |
| ☑ | **Write from code, not from a sibling spec file** — §2 step 4. These sections are absent, so there is nothing to proofread and no temptation to copy a neighbour. |
| ☑ | **`Status transitions` on `Collection`, `Folder` and `MediaChangeRequest` are real gaps — do not exempt them.** Confirmed against code 2026-08-25: `Collection.Status` (`Active`/`Archived`), `Folder.Status` (`Active`/`Archived`), and `ChangeRequest.Status` (`Open`/`Resolved`/`Abandoned`, guarded in the aggregate). All three have enforced state machines that the spec does not state. *(Note the class is `ChangeRequest`, not `MediaChangeRequest`.)* |
| ☑ | **Two renames are rename-and-rewrite, not rename-only.** `Collection` and `Folder` answer `Handler-side Pre-conditions` with `## Constraint Enforcement — Implementation Notes`. Folder's is a genuine pre-condition list; **Collection's is narrower** — reservation mechanics and handler call sequences, not a guard enumeration. Compare against the canonical form, `mediaitem.write-model.md`'s 17-row `Handler / Service / Guard type / Condition` table. Renaming Collection's without rewriting it blesses a partial answer as complete. |
| ☑ | **The 35 renames** (`--show-renames`): normalise to the canonical heading. Mechanical apart from the two above, but do it in place per file — never a whole-file rewrite (W1). |
| ☑ | As each category empties, flip its line in the script's `OWNER_SEVERITY` table from `warn` to `fail`. |

**Done 2026-08-25. Zero `[unowned]` findings and an empty rename backlog** — the two numbers this unit
exists to drive to nothing. Section warnings 119 → 102; what remains is W9 (72), BI-1 (16), W25 (10),
W28 (2), W22 (1), W23 (1), every one owned.

**The 17 gaps split three ways, and only the first group was the mechanical job this unit assumed.**

- **Six were genuinely missing prose** — `Related` / `Related Specifications` on four files, and a
  `Diagram Key` for `asset.scenarios.md`. That file documents **HTTP request/response exchanges rather
  than sequence diagrams**, because the client talks to S3 directly and the wire traffic *is* the
  behaviour — so its key documents that notation instead of inventing participants.
- **Six were renames in disguise.** `Processing/context-overview.md`'s three "missing" sections were
  present as *Aggregate Ownership*, *Services* and *Pipeline Logic*. Renamed, and the event-flow section
  gained the fact the old heading buried: **the pipeline has two exits**, and which one an asset takes is
  decided before processing starts.
- **Five needed real content written from code**, and those are below.

**`processingjob.api.md` has no HTTP API at all, and that is the answer.** No
`Processing.WriteModel.Endpoints` project exists — the only module without one — `Api.csproj` references
only the infrastructure, and **`QueryApi` does not reference Processing at all**. All six commands are
dispatched in-process by workers, the saga and the timeout scanner. The three sections now say so
explicitly rather than being absent, because an absent `Write Endpoints` reads like an oversight and this
is a design decision. **A processing job cannot be created, retried or cancelled by a client.**

> **New finding — X-11.4.** Chasing that turned up two read models **built and paid for with no reader**:
> `media-processing-job` and `media-processing-jobs` are projected on every job event and their GSI is
> maintained, but nothing can query them. `GetProcessingJobByIdQuery`'s handler is registered only in the
> `Api` host, which has no Processing endpoints; `ListProcessingJobsForAssetIdQuery` **has no handler
> registered at all**. Either expose them or stop projecting them.

**Three status-transition sections were written and each surfaced something.** `Collection`: **only
`Rename` refuses on an archived collection** — `ApplyTags`, `SetDefaultMediaProfile`, `SetVisibility` and
`UpdateDescription` have no archived check, so an archived collection can still be **made public**.
`Folder`: **`ClosedAt` is an orthogonal flag, not a status** — nothing else guards on `IsClosed`, so a
closed folder can still be renamed, moved and metadata-edited. `MediaChangeRequest`: `Resolved` and
`Abandoned` are both terminal with no reopen, **state is checked before authorization** (CR-19), and
**`EditComment`/`DeleteComment` do not check `IsOpen`** — comments on a closed request are still editable.

**`kind` is derived, not stored, and nothing enforces it.** `governance` / `commentThread` is computed at
map time from whether `ReviewSessionId` is empty. There is no uniqueness constraint and no per-item
open-request count anywhere in ChangeRequests — **the "two live at once" pairing is enforced by Catalog**,
on `MediaItem.ReviewSession`. The aggregate imposes no cardinality at all.

**Two renames were correctly identified as rename-*and*-rewrite, and the rewrite is what mattered.**
`Collection` and `Folder` answered *Handler-side Pre-conditions* with
`## Constraint Enforcement — Implementation Notes`. That section is organised by **mechanism** —
reservation tiers, locking, non-atomicity — which is worth keeping, but it is not a guard enumeration, so
a reader could not answer *what must be true for this command to be accepted?* from it. **Renaming it
would have blessed a partial answer.** Both files now carry a real guard table derived from the handlers,
with the mechanism narrative left in place beneath it.

**Also corrected while in the file: `folder.write-model.md`'s `ExpectedVersion` invariant is false.** It
claimed `ExpectedVersion` must match `Version` on *all mutating commands* with a `ConcurrencyConflict`
error. **No Folder command carries an `ExpectedVersion` field.** Concurrency is the event store's
conditional write, retried 3×; **a client cannot currently express "only if unchanged" against a folder
at all.** The row is struck through rather than deleted, because callers may have been written against it.

**Three "Value Object" renames were not renames either.** `RecordType`, `MediaProfile` and `Registration`
give each value object its own `## <Name> Value Object` section. Renaming one of several to `Value
Objects` would have been wrong, so each file gained an umbrella heading above its per-type sections.

**Not flipped to `fail`:** W30 has no rule of its own — its findings reported through `required-section`,
whose severity is now keyed by the *owning* unit. With zero unowned findings there is nothing left for a
W30 line to gate, which is the correct end state.

**Done when.** `check-spec-sections.py` reports zero `[unowned]` findings and an empty rename backlog.
Full green also needs W5, W9, W22, W23, W25, W26, W28 and a BI-1 decision — this unit closes only its own
column.

**Also, and it is not this unit's:** **W28's steps name only `Folder` as lacking `Value Objects`; it is
`Folder` **and** `Collection`.** Fix that in W28 before working it.

**Touches.** ~12 spec files, `.github/scripts/check-spec-sections.py` (`OWNER_SEVERITY`).

---

## 6. Exit criteria

Deliberately checkable, not aspirational. Every criterion names the unit that delivers it; every unit
appears against at least one criterion.

| ✓ | Criterion | Unit |
|---|---|---|
| ☑ | No file in `docs/spec/` ends mid-construct, and **CI fails if one does** — *CI half done 2026-08-25 (W1); closes fully at W18, when the five marked exceptions and the `_recovered/` exclusion go and the guard becomes unconditional* | W1, W18 |
| ◑ | Every file type satisfies its required-sections contract, enforced in CI and green — *check landed 2026-08-25 (W2), running on every `docs/**` PR.* **Every unit in the backlog is now closed** — W5, W9, W22, W23, W25, W26, W28, W30 — and the run reports `fail 0 · warn 16 · rename backlog 0`. **All 16 remaining warnings are BI-1**, so this criterion is one decision away from green: build the bulk-import feature, delete its spec, or badge it as design. | W2 · **BI-1 only** |
| ☑ | No `[unowned]` finding and no rename backlog in `check-spec-sections.py` | W30 · *done 2026-08-25* |
| ☑ | `spec/README.md` answers "which file owns this question" for all 16 dimensions | W3 · *done 2026-08-25* |
| ☑ | Every contradiction still open is visible **in the repo**, with an owner | W4 · *done 2026-08-25 — 14 contradictions + 6 gaps* |
| ☑ | **One glossary**, containing every term the 2026-08 corrections introduced; no other file defines terms | W5 · *done 2026-08-25 — enforced in CI* |
| ☑ | **One file answers context ownership and one answers the host inventory** — the 8 / 9 / 12 disagreement is gone, every context relationship has a type, and `bounded-context.md` and `service-boundaries.md` are both deleted with no inbound links | W6 ☑ · W7 ☑ — `architecture/bounded-contexts.md` owns ownership and relationship types; `domain-model.md` owns the single **nine**-aggregate inventory, with the three specified-but-unbuilt named separately |
| ☑ | **One aggregate inventory**, and the reference-by-id + one-aggregate-per-transaction rules are stated once | W7 · *done 2026-08-25* |
| ☑ | `system-spec.md` does not exist; all 19 of its sections are findable from `spec/README.md`, and no new `shared/` file shares a basename with a `docs/adrs/` file | W8 · *done 2026-08-25* |
| ☑ | Every spec file carries `_Last reviewed:`, and no link points at a deleted file | W9 · *done 2026-08-25 — enforced in CI* |
| ☑ | **Every question has one answer** — for each Tier-1 and Tier-3 contradiction, exactly one document states the rule and the others link to it or are deleted | W10 (T3) ☑ · W4, W11, W12, W22, W23 (T1) ☑ — **all complete 2026-08-25.** Q-1, Q-2, Q-6, Q-8, Q-9, Q-10, Q-13, Q-14 and G-1 to G-6 closed; the seven still listed in `open-questions.md` are open by decision, not by neglect |
| ☑ | One integration-event naming scheme survives in the spec, with an ADR; the loser is deleted, not aliased | W11 · *done 2026-08-25* |
| ☑ | Read-model table names match the CDK | W12 · *done 2026-08-25* |
| ☑ | `docs/spec/_recovered/` does not exist and no `⚠ TRUNCATED` marker survives | W13–W18 · *done 2026-08-25* |
| ☑ | **Every saga and process manager has an owning file** to the W2 contract — including the two fan-out workers that are process managers without the name | W19 ☑ · W21 ☑ — three files: `assetingestionsaga.md` (real), `archive-fan-out.md` (two live process managers), `documentsigningsaga.md` (design only) |
| ☑ | No spec file references `MediaItemReviewSaga` **as a live mechanism** — eleven files still name it, every one dated and pointing at the replacement | W20 |
| ☑ | **Every privileged command's authorization is stated**, with the long tail enumerated and dated | W22 |
| ☑ | MediaItem's three state machines have one interaction table, and `Capability` has a specified home | W23 |
| ☑ | **Cascade and cross-aggregate invariants are stated once**, in the spec tree rather than in an ADR | W24 |
| ☑ | A projection-lag bound and a read-your-own-writes rule exist, and every read model states its lag class | W25 |
| ☑ | Every aggregate has a `scenarios.md`; Folder's archive cascade and subtree move have worked examples | W26 · *done 2026-08-25 — enforced in CI* |
| ☑ | `BULK-IMPORT-SPEC-UPDATES.md` is gone and nothing it uniquely held was lost | W27 — only the SQS/DLQ queue config was unique; it is in `bulk-operations.md` |
| ☑ | The entity-vs-VO rule is stated **and applied** — no entity catalogued as a value object | W7, W28 |
| ☑ | Tier 2 client-contract items resolved; the spec no longer claims idempotency support it does not have | W29 |
| ☑ | *(Drift review, not closed by this plan)* No traceability table names a class that does not exist | **X-11.1 ☑ closed 2026-08-25** — 145 references across 28 files rewritten to name the **read-model table** rather than an invented class. Decision: tables, not classes, because one event can be handled by nine projectors across three modules. |

---

## 7. Risks

- **Stage A slips and the rest proceeds anyway.** Every later unit writes to these files. Without W1 one
  wholesale rewrite re-cuts a file and silently discards the work; without W3 the next person needing an
  answer writes it wherever they are standing, and the duplication this plan deletes grows back behind it.
- **W8 is the highest-risk single unit.** Splitting a 1,200-line file that many things link into, while
  part of it is still truncated. Do it after W5/W6/W7 have already taken three sections out, so the split
  is smaller than it looks — and edit in place, section by section, never wholesale.
- **W22 may find real authorization gaps, not documentation gaps.** Anything the code does not enforce
  becomes a security finding with its own urgency and stops being a spec task. Do not let it queue behind
  the rest of the matrix.
- **A structure guarantees one answer, not a right one.** X-11.1 is the proof: the traceability tables are
  in exactly the right file and wrong 88 times. Every unit here should verify against code, not against a
  sibling spec file — that is why step 4 of §2 exists.
- **Some quarantined prose will disagree with code about behaviour, not naming.** Two ~3 KB blocks of
  months-old text are big enough to hide a real drift finding. W13 and W14 should expect to file one.
- **The wiki is a recovery asset and nothing protects it.** Seven of the fifteen recovered tails existed
  only in `Media.wiki`'s history. It is correctly described as a lagging generated copy that should not be
  hand-edited — and it is also the sole surviving source for a uniqueness contract and three DR runbooks.
  **Do not let the planned auto-publish workflow force-push or rewrite that repo before Stage C closes.**

---

## 8. Session log

One line per session. Newest last.

| Date | Units | Notes |
|---|---|---|
| 2026-08-25 | W0 | Recovery, dating, quarantine, code check. Raised X-11.1. Plan restructured into units. See §9. |
| 2026-08-25 | W1 | `docs-guard.yml` + `check-spec-truncation.py`. Fails on the 2026-08-24 tree (40 findings / 23 files), passes today (72 files). Found an **18th** truncated file — `mediaitem.read-model.md`, cut inside a code fence since `d0adc7bc` (2026-07-19), missed by the W0 sweep because it kept its trailing newline; recovered from `6fc139ee` with the `MediaItemStatus` enum corrected against code. **§9.1's counts are superseded — see the note in W1.** `CLAUDE.md` carries the never-rewrite-whole-file rule. W2 is now unblocked. |
| 2026-08-25 | W2 | `check-spec-sections.py`, second step of `docs-guard.yml`. Contract measured against the tree: **53 missing sections across 31 of 72 files** — far past this unit's five predicted failures, because the contract was written from MediaItem and most files never matched it. Two calls taken (Chase, 2026-08-25): **everything ships at `warn`, flipping to `fail` per owning unit as each closes** (severity is keyed by unit, not by rule — five units share one rule), and **synonyms are accepted but logged as a 35-item rename backlog**. Verification caught 6 false gaps from an incomplete synonym map, moving unowned 22→19 and W28 5→2; two unsound synonyms removed. Every finding names its owning unit; **19 named none, so W30 was added** (+1½ d to Stage E). Also corrected: effort headline 21½→21¾, §4's X-11.1 count 69→88, W28's step now names Collection as well as Folder. Exit 0 today. |
| 2026-08-25 | W3 | `docs/spec/README.md` — the question map. All 16 dimensions plus 4 rows the review's sketch lacked; every *(planned)* row also says where the answer lives today. Linked from the repo `CLAUDE.md` **and** `docs/README.md`. No `W`-numbers in it — they point at a plan on `Z:\` that two of three engineers cannot open. **W6 must repoint rows 2, 3 and 10** when the architecture merge lands (noted in W6). **Verification caught 3 factual errors, all inherited from the structure review's §1 and stated more confidently than the review stated them** — worst was row 10 forbidding `bounded-context.md`, the sole owner of the only relationship-type table in the tree. Fixed here and corrected in W6, which inherits the same two claims. New finding for W9: `adrs/README.md` lists **`deployment-and-resource-naming.md`**, which has never existed in any revision; a link sweep found 3 dangling links outside `_recovered/`. W4 gained a step to give the map's *(planned)* rows in-repo anchors. |
| 2026-08-25 | W4 | `docs/spec/open-questions.md` — **all 14** Tier-1 contradictions (`Q-1`…`Q-14`), not the 5 this unit named, plus 6 known gaps (`G-1`…`G-6`) giving the README's *(planned)* rows in-repo anchors. **All 14 verified against spec and code first**, then verified again — the second pass found **Q-4 materially wrong** and reversed its character: the evidence-destroying hard-delete is **live shipping code**, not an unbuilt contract, making it a product decision for regulated-records customers rather than an editing task. Seeding only the named 5 would have hidden it entirely, along with **Q-12** 🔒. Nine entries are settled by existing evidence (6 code, 1 CDK, 2 spec). Owner is a person on every row, never a `W`-number. Also fixed a stray `z` breaking `bounded-context.md`'s H1. **Stage A's work is done — but three of its files are still untracked and `docs-guard.yml` is committed calling one of them, so docs CI is red on `develop`. Commit before continuing.** |
| 2026-08-25 | — | **Diagram pass on `bounded-context.md`** (Chase's request, outside the unit board). Transport Topology, the five Saga Event Flows and Queue Topology redrawn as **mermaid** — renders on GitHub and the ADO wiki, stays diffable and code-reviewable, which an image would not. All 7 blocks validated against mermaid 11. **Redrawing them surfaced structural drift the diagrams had been hiding:** `media-sagas` and `media-processing` subscribe to **`media-integration-events`**, not the domain topic; **`media-signing` does not exist**; **`media-projector-search` was missing from the spec entirely**; two visibility timeouts were wrong. All corrected in this file and raised as **X-4.14** for the copies in `system-architecture.md` / `system-spec.md`, plus **X-4.15** (two SNS filter policies are unenforced hand-mirrors of C# registrations — this has already silently broken CR-21 once). Saga diagrams now carry 🟢 live / 🟡 deferred / ⛔ never-built badges, so `MediaItemReviewSaga` cannot be built from by mistake. Translation node named `*DomainEventMapper` per X-3.3 rather than repeating the wrong `*IntegrationEventPublisher` claim. |
| 2026-08-25 | — | **Diagram pass on `bounded-context.md`, part 2.** Bounded Context Map redrawn as mermaid with the **relationship type on every edge** — this file solely owns those (W3 row 10), so the map now carries them visually. Corrected against `src/hosts/`: the old map drew the 2026-03-11 topology `service-boundaries.md` was rewritten to repudiate — *Ingest API*, a *Command Handler* Lambda and a *SecuredSigning Adapter* that **do not exist**, one *Projectors* box that is really two hosts, and no `EventConsumers` or `TimeoutScanner` at all. **Its nine-aggregate inventory was removed**, closing one of the three competing inventories and pre-empting a W6 step; `domain-model.md` owns it. Also fixed: "quota-exempt" → deferral (S12/Q-3), and the `AssetIntegrationEventPublisher` → `AssetIntegrationEventMapper` naming (X-3.3). **The file now contains zero ASCII diagrams** — 8 mermaid blocks, all validated against mermaid 11. `## Internal Services` and `### Per-Service Event Contracts` still carry the fictional service names in ~20 prose references; banner-flagged, not rewritten — noted in W6 as the merge's real work. |
| 2026-08-25 | W5 | `docs/spec/glossary.md` — **68 terms**, merged from all 8 sources, which are deleted. W2's `forbidden-section` rule **flipped warn → fail** and verified biting; section-check warnings 128 → 122, W5 off the backlog. **Four rows the corruption had swallowed were recovered** from `Media.wiki` blob `ba5debc2` — `Event Store`, `Integration Event`, `Projection`, `Saga` — and three existed in **no other glossary**, so a straight merge of the seven survivors would have lost them silently. Nine conflicts resolved: the two that would have produced wrong code were **`Standalone upload`** (AssetManagement still carried the "full pipeline" rule `domain-model.md` retired by name) and **`DocumentSigningSaga`** (described in the present tense; the class does not exist). Also fixed `Validation`'s trigger, `Version`'s command, `Capability`'s false absolute, and `Document …` — four spellings covering two different referents. Three terms are deliberately multi-sense. `AssetIngestionSaga`'s three-way creation-trigger conflict was **left to G-5**, not invented away. **G-1 closed and deleted.** |
| 2026-08-25 | W13 | DDD-T11 rewritten from `Metadata.WriteModel` + the platform SDK; marker and `_recovered/` file deleted (**3 markers left**). The step said "confirm, do not assume" about three details "most likely to have survived" — **all three were wrong**, along with the transaction model, the conflict handling (stated as the exact inverse of the code), the event names and the publisher class. **Exactly one claim survived: the table name.** Both missing integration-event sections written, closing **2 of W30's 17** unowned findings. 🚨 **Found a live production bug — X-4.16 (High):** `media.recordtype.*` is absent from the `media-cross-module-events` allowlist, so three registered Catalog consumers can never run and **a deprecated RecordType is never marked deprecated, leaving `MediaProfile` free to pin it.** That is **X-4.15's failure mode landing within a day of being raised** — the proposed build-time allowlist check should be treated as due. |
| 2026-08-25 | W15 | DDD-T10 landed; marker and `_recovered/` file deleted (**2 markers left**). `AssetUploaded` confirmed never to have existed — but checking that one name exposed a worse error in the text that *survived*: the section was headed **`media-assets`** and called the data "owned by AssetManagement", **describing a boundary violation the code does not commit**. Catalog maintains its own index, `media-catalog-asset-ref`, from integration events. Field names, delivery queue and the whole subscribed-event table were wrong — it named a non-existent event, two the projector does not handle, and **omitted `AssetInfectionDetected`**, the compliance path behind Q-4. **Also documented `media-catalog-change-request-ref`, a live reference model the spec covered nowhere** — the plan's prediction held exactly: `Resolved`/`Abandoned`, never `Approved`/`Rejected`. Note for W20: it stores a boolean `IsOpen`, not a status. Two salvage units in, the pattern is consistent — **link lists survive, tables naming code do not.** |
| 2026-08-25 | W16 | DDD-T12 written from `AssetJobIndexProjector`; marker gone (**2 left**, both W14/W17's). **This unit's step pointed at the wrong section** — it named the two read-model projectors, but the cut is in `## Write-Side Reference Models` → `AssetProcessingJobIndex`, maintained by `AssetJobIndexProjector`; the marker named a third class, `ProcessingJobProjector`, which does not exist (X-11.1). **The truncated sentence was about to state something false**, which is the finding: it read *"Mirrors current job statu…"*, and the projector writes **`Status = Running` on both terminal events**, so a row never reaches `Succeeded` or `Failed`. Nothing is broken today because **nothing reads the field** — both consumers use the index only for the `AssetId → JobId` lookup, and the scanner filters on the *saga's* status in a different table. That makes it a trap with a plausible name, not a live defect: raised as **X-4.17 (Med)**, fix the writes or drop the field. Third salvage unit, third time the *surviving* text was worse than the lost text — Stage C's value has been the code reading it forces, not the prose it recovers. |
| 2026-08-25 | W17 | DDD-T17 written from both workflows. **One `⚠ TRUNCATED` marker left tree-wide** (T16, W14's). The cross-check step earned its place: the cut was inside a bullet about **cdk's** trigger, so writing it only from `build-and-push.yml` — as the step said — would have documented the wrong dispatch. **Two entry points, different jobs:** build-and-push *produces* an artifact and hands off by committing the tag; cdk's deploy.yml *deploys* one that exists. Documented both, plus three traps: a gated dispatch is **skipped, not failed** (a green tick can mean nothing happened), staging has no config file and deploys qa.json, and a missing `imageTag` is a hard failure. 🔒 **Surfaced into the spec: there is no platform-enforced approval gate on staging or prod** — no required-reviewer protection is attached (org not on Team plan), so "Tom approves" is convention, not enforcement. That was buried in a `deploy.yml` comment and stated nowhere a spec reader would find it. |
| 2026-08-25 | W26 | All three missing `scenarios.md` written; **W26 off the backlog and its rule flipped `warn` → `fail`**, verified biting. `folder.scenarios.md` is greenfield — no blob in either repo, ever — and written from code, which **contradicts the aggregate's own comments in three places**: the archive cascade is **write-side and synchronous** (not a projector flipping `isAccessible` via a GSI that does not exist), `FolderHasActiveChildren` is not a real error code, and the registration check is blocking, not a warning. **Note the direction — the spec file was right and the code comments were wrong**, the reverse of most findings. Raised as **X-11.2**. Also **X-11.3**: the cascade has **no resume path and swallows descendant failures**, so the target folder archives even if every descendant failed and the caller still gets `204`; a successful archive also logs a burst of `Failed to archive…` warnings from recursive re-entry. Corrected `folder.write-model.md`'s cross-collection-move gap, which was understated: the **descendant aggregates** hold the stale `CollectionId`, so **a rebuild reproduces it rather than repairing it**, and the subtree stays visible in the source collection's hierarchy. Both bulk files are marked ⚠ intent throughout and document what the design does *not* answer — no compensation, no dedup, no timeout on a phase that waits on a third party. |
| 2026-08-25 | W30 | **Zero `[unowned]` findings, empty rename backlog** — the two numbers this unit exists to drive to nothing. Warnings 119 → 102, all remaining owned. The 17 gaps split three ways: 6 genuinely missing prose, **6 renames in disguise** (Processing's three were present as *Aggregate Ownership* / *Services* / *Pipeline Logic*), and 5 needing content from code. **`processingjob.api.md` has no HTTP API at all** — no endpoints project, `QueryApi` doesn't reference Processing — and the sections now say so rather than being absent. That turned up **X-11.4**: two ProcessingJob read models are projected on every event with **no reader**, one query having no registered handler at all. Status-transition sections surfaced three live oddities: an archived Collection can still be **made public**; Folder's `ClosedAt` is orthogonal to status so a closed folder is still editable; ChangeRequest comments stay editable after the request closes. **`kind` is derived, not stored** — the two-live-at-once pairing is enforced by Catalog, not here. The two `Constraint Enforcement` renames were correctly rename-**and**-rewrite: that section is organised by mechanism, not guards, so renaming would have blessed a partial answer — both files gained real guard tables. Also corrected `folder.write-model.md`'s **false `ExpectedVersion` invariant**: no Folder command has one, so a client cannot express "only if unchanged" against a folder at all. |
| 2026-08-25 | W6 | `architecture/bounded-contexts.md` created from `service-boundaries.md` as base; **both source files deleted**, zero stale inbound links tree-wide, zero broken links. Carried over `bounded-context.md`'s `Context Relationship Types` table — the only one in the tree — and **typed the seven internal relationships, which had none anywhere**: every internal edge is Published Language over `media-cross-module-events`, except **Metadata → Catalog, which is Conformist**. Dropped its aggregate inventory (closing one of three), event catalogues, and the never-built `Internal Services` / `Per-Service Event Contracts` topology. **The runtime sections — transport, saga flows, queue topology and config, all four corrected diagrams — moved to `system-architecture.md`**, which owns queues and topics. **The merge carried two contradictions and both were caught and fixed in the merged file**: the stale "quota configurable" claim (Q-14) and "standalone runs the full pipeline" (Q-3). **Q-14 is closed** — both its sides lived only in the two deleted files. Q-1 and Q-3 each lost a side. D3 applied within the new file: 14 × `media.mediaitem.*` → `media.item.*`. README rows 2, 3, 10 and 12 repointed; glossary and open-questions retargeted. |
| 2026-08-25 | W7 | `domain-model.md` rebuilt around the three things it owns. **The 9/10/12 disagreement is settled at nine**, taken from the `[AggregateType]` attribute — the only place an aggregate is declared. **The reason nobody could reconcile it by comparing lists: the number depends on whether you count specified-but-unbuilt aggregates.** `DocumentSigningSession` and the two bulk jobs are now named separately, every time. Two class names also differ from the spec's — the aggregate is `ChangeRequest`, and MediaItem's type string is `media.item`, which is the same fact that settles Q-1. **Wrote the cross-aggregate relationship model, which existed nowhere** — every reference is by id, no aggregate holds a child list, and the one deliberate exception is `MediaProfileSnapshot`, a snapshot rather than a reference. **Stated the three rules that were implied everywhere and written nowhere**, including a defence of the name-reservation/event-append seam (X-9.6): reserving first makes the failure mode a *stuck name* rather than a *duplicate name*, and atomicity would couple the uniqueness registry to the event store's partitioning. Absorbed `Naming Conventions` from `system-spec.md` (W8 expects it gone). Deleted the header's claim that `specs/media-management-domain-spec.md` is authoritative — **that file has never existed**. |
| 2026-08-25 | W8 | `system-spec.md` **deleted** — split into five `shared/` files, **no stub**. All 15 remaining content sections landed; three had already been taken out by W5/W6/W7 and the Table of Contents was discarded, so nothing is unaccounted for. **Zero links anywhere still target the file**: 31 anchors repointed to their new homes, 5 stale link labels fixed, and the only broken links left tree-wide are the same 3 pre-existing ones W3 logged. The DR truncation marker travelled with its section into `operations.md`, so **W14's target is still marked**. `Cross-Context Relationships` was found to be a strictly inferior duplicate of what W6 had already written — stale host names and dependency *types* rather than DDD relationship types — so it was dropped rather than absorbed. None of the five new basenames collides with `docs/adrs/`; the plan's warning about `persistence-and-eventing.md` was confirmed, which is why the event file is `event-store-and-messaging.md`. **Releases W9, W10, W12, W14 and W19.** |
| 2026-08-25 | W9 | **All 81 spec files carry `_Last reviewed:`** and the rule is **flipped `warn` → `fail`**, verified biting. Section warnings 98 → 30, and **every one that remains is owned** (BI-1 16 · W25 10 · W28 2 · W22 1 · W23 1). Dates come from each file's last commit rather than today's — 27 kept a real historical date; **41 legitimately read 2026-08-25 because this session edited them.** **Zero broken links across all of `docs/`, not just `docs/spec/`.** The three W3 found are resolved: `RUNBOOK.md` existed all along at `src/tools/ProjectionReplay/` and the link was simply pointing at the repo root; ADR-010's archive link pointed at a pre-migration `repos/magiq-media/…` path and was demoted to plain text rather than repointed, since it is an archived ADR; and `adrs/README.md`'s **`deployment-and-resource-naming.md` row now says plainly that no document exists** — `git log --all` finds no commit that ever added it — with the choice stated: write the ADR or delete the row. |
| 2026-08-25 | W10 | Tier-3 swept. **Over half the list had already been closed by earlier units** — the host inventory by W6, `MediaItemStatus` partly by W1, the projector counts and the checkout model when `system-spec.md` was deleted in W8 — which is what the plan predicted would happen if Stage B ran in order. Five were still live and **all five are settled by code, none needed registering**: `ITenanted` does not exist (`ITenantScoped`, 19 uses); the third S3 bucket is `media-quarantine`, not "docs" (fixed in the repo `CLAUDE.md` stack table); Registration has **no `ExpiresAt`** — no event carries it, no projector writes it — which matters because `PendingConfirmation` then waits on an external authority forever; and `asset.scenarios.md`'s virus path carried **three values that would not compile or parse**: `InfectionDetected` is neither an `AssetStatus` (it is `ContainsVirus`) nor a `FailureCategory` (five members, and `Enum.Parse` would throw), because virus detection is a distinct `ValidationOutcome.VirusDetected`. That same scenario's step 7 still claimed the object is moved to quarantine; corrected to the hard-delete that ships, pointing at **Q-4**, which stays open as the compliance decision. |
| 2026-08-25 | W11 | `media.mediaitem.*` **deleted from every spec file, not aliased** — an external SNS filter policy cannot match both spellings, so an alias would leave four downstream contexts guessing. ADR written into `adrs/persistence-and-eventing.md` § *Integration Event Naming* and indexed. **Q-1 closed.** **The step said this was a deletion sweep; it was not.** `media.mediaitem.published` was the wrong *event*, not just the wrong spelling — **there is no `media.item.published`**; a MediaItem going live raises `media.item.approved`. A find-and-replace would have produced spec references to an event that does not exist, in three files. Two further fictions surfaced: `media.mediaitem.signing-session-voided` (DocumentSigning publishes **no** integration events at all, so that notification step has no mechanism behind it), and the aggregate segment does not track the class name — `MediaItem` → `item`, `MediaChangeRequest` → `changerequest`, so `[AggregateType]` is the authority, not the C# type. Also repointed **10 stale `shared/system-spec.md` references in `open-questions.md`** — W8 deleted that file and the register was still citing it. |
| 2026-08-25 | W12 | **62 `-detail` spellings corrected across 21 files.** The CDK manifest provisions **24 tables and not one ends in `-detail`** — detail tables use the singular base name. **Q-8 closed.** Scoped at ¼ d on the assumption the contradiction sat in two places; it was in **21 files**, because the wrong name had propagated into scenarios, API traceability tables and projector lists long after the inventory itself was corrected. **The 22 `-detail` names left are deliberate:** they belong to `media-signing-session-detail` and the two bulk-import tables, **none of which is provisioned**. Renaming them would invent a provisioned name for an unbuilt table, so they stay as written and the convention note says why. Convention recorded in both `event-store-and-messaging.md` and `operations.md` — the two halves the old self-contradiction had split across. **Releases W29.** |
| 2026-08-25 | W14 · W18 | DR runbooks rewritten into `operations.md`; **the last `⚠ TRUNCATED` marker and the last `_recovered/` file are gone, and the folder is deleted. Stage C is complete.** **The recovered runbooks would not have worked during an incident** — four corrections, each against the CDK: five Lambda names were fictional (and the eight real ones don't match the host project names either); **the rollback procedure could not be executed at all** — it said `aws lambda update-alias --name live`, and **no Lambda alias of any kind is provisioned**, so rollback is a redeploy of a previous `imageTag`; the read-model table-swap step named an SSM key that does not exist, when projection tables are schema-versioned behind a `read-model-metadata` pointer flipped by `ProjectionReplay`; and the rebuild command was not the tool's interface. **Backup verification: no schedule exists and nothing tests that a restore works.** The recovered table proposing one was cut mid-cell and could not be reconstructed *because no schedule was ever implemented* — so the section states the gap rather than inventing a cadence. **W18 then made the guard unconditional**: the `⚠ TRUNCATED` exemption and the `_recovered/` exclusion are both removed, verified — a marker no longer exempts a bare cut. `CLAUDE.md` now documents recovery-from-history as the response to a truncation, not marking. |
| 2026-08-25 | W19 | **`contexts/Processing/sagas/assetingestionsaga.md`** — the file type exists and the only real saga is specified to all nine sections. **G-5 closed**; README row 12 is live. **The bypass-exit hole this unit flagged as a possible live defect is a false alarm** — `Bypassed` is a *fifth* state the saga assigns to itself before dispatching, so the branch terminates synchronously and the scanner never sees it. The premise came from the saga's own XML doc, which lists four transitions and omits the branch. **Documentation gap, not a code bug.** Filed in `Processing`, not `AssetManagement`, against the file-type rule: the outcome is AssetManagement's but the class, state, all five handlers, the compensation target and the creating trigger are all Processing's — reasoning recorded in the file. **Three real code findings instead**, and one is serious: **X-11.6 (High)** — both handler layers swallow exceptions and the inner never rethrows, so the outer always returns `Success()`, **the message is acked and the event is lost**; `maxReceiveCount: 3` never counts and the DLQ alarm cannot fire, while both log lines promise a retry that never happens. **X-11.5** — compensation is not the no-op its comment claims, so after a validation timeout the **ProcessingJob stays `Queued` forever**. **X-11.7 (needs confirming)** — `AssetProcessingWorker` is registered but resolved by no host, and it looks like the only dispatch site of `CompleteProcessingJobCommand`. Also corrected **three errors in `saga-patterns.md`**: wrong creating trigger, compensation aimed at the wrong aggregate, and the entire `AwaitingValidation` scanner pass missing. **Releases W20 and W21.** |
| 2026-08-25 | W20 | **The unit's own premise was false, and this time it mattered.** The plan called `MediaItemReviewSaga` a saga that *"does not exist"*, and five spec files said *never built*. **It was built.** `MediaItemReviewSaga.cs` + state + status were real, five handlers were **registered in `SagaRegistrations`**, and it shipped on `develop` and `release/1.0.0` — never on `main`. It was deleted **2026-06-02** (`7d1f32e5` PR #81 → `cc7f9be8` PR #83) in the same commit that replaced it with an embedded `ReviewSession` on `MediaItem`. The distinction is not pedantry: *"never built"* invites someone to build it, and the argument against it is recorded on `ChangeRequest` itself — a review saga *"would convert a local invariant into a distributed one guarded by a saga — strictly weaker, for no gain."* That reasoning is now preserved in `saga-patterns.md` rather than lost with the code. **A stale `bin/Debug` XML doc is what gave it away** — the source tree was clean. Scope was **4 files in the plan, 11 in reality.** Beyond the name: `domain-model.md`'s whole `MediaChangeRequest` section was rewritten (wrong status values, a `Reviewers` field the aggregate does not have, **six events that do not exist**, and the resolution direction **inverted**); `Catalog/context-overview.md`'s reference-index table named two nonexistent integration events and a `Status` field that is really a boolean `IsOpen`; `mediaitem.read-model.md` projected `MediaChangeRequestLinked`/`Unlinked` (no such events) and claimed `Status = Rejected`/`Withdrawn` (**no such statuses**); the saga diagram in `system-architecture.md` was replaced with the real no-saga flow. **`security-scenarios.md` PERM-2 was wrong in every particular** — there is no `RequireActorType` policy, no `ActorTypeForbidden` code, the route did not exist, and the endpoint it called System-only is the **opposite**, reviewer-only, refusing system actors. Rewritten around `ForceReleaseCheckout`, which is System **or owner**. That let **Q-13 (🔒) close** alongside Q-2, and corrected two false authorization rows in `multi-tenancy-and-auth.md`. Three new findings: **X-11.8** orphaned-but-registered `RejectMediaItemCommand`, **X-11.9** a 403 with no `errorCode`, **X-11.10** four private copies of `SystemActorType`. **Verification note:** the link checker used in earlier units was too lax — a corrected slugifier finds **11 pre-existing broken anchors** tree-wide (none from this unit; the 2 W20 caused were fixed), and mermaid validation finds **5 pre-existing invalid diagrams** in four `*.scenarios.md` files. Neither is W20's, both are now known. |
| 2026-08-25 | W21 | Two files. **`documentsigningsaga.md` — design only, and the gap is bigger than 'deferred' implied.** There is no saga class, no saga state, no status type, **and no `DocumentSigningSession` aggregate either** — `DocumentSigning.Domain/Aggregates/` holds an `Events/` folder and nothing else, so the docs project's CLAUDE.md was right and the repo's was wrong (**X-11.11**, fixed). The host is misnamed: nothing in `SagaOrchestrator.DocumentSigning` is a saga — it is an anti-corruption adapter, and both its handlers are `NotImplementedException`/HTTP 501. **Three spec claims killed:** the 72-hour timeout has **no source in code** (no scanner, no options class, no config section, no `72` anywhere); `TimeoutScanner` hard-codes `SagaType = "ASSET_INGESTION"` so a signing scanner is new code, not config; and the checkout story was backwards — `ActiveSigningSessionId` is a mutual-exclusion flag that **blocks** checkout, not a lock signing acquires, so compensation is `UnlinkSigningSession` and **`ForceReleaseCheckout` has no connection to signing at all**. Correlation key settled as `SigningSessionId` on evidence (only id on all nine events; the projector keys on it; `EnvelopeId` does not exist at saga creation and is a *tenant-resolution* lookup). **The fan-out half is where the live findings are.** `CollectionArchiveFanOutWorker` and `FolderArchiveFanOutWorker` are in production and were unspecified; written to the saga contract deliberately, so each missing section had to be stated as missing. **X-11.16 (High)** — every per-child failure is logged and discarded, and *"Fan-out complete"* prints whether all 900 items archived or none did. **X-11.17 (High ⚖️)** — `ArchiveCollectionHandler` has no registration guard (verified) and archives *before* the cascade, so a collection holding retention-locked folders reports archived while its locked folders stay active, with no rollback and no record. Plus **X-11.15** re-entrant cascade doing O(depth) work, **X-11.18** the traversal index prunes archived children so a retry sees a smaller tree *(flagged for confirmation, not asserted)*, and **X-11.19** the cascade is synchronous in-request on dev/qa/staging and async over SQS on prod alone — confirmed against `magiq-media-stack.ts`, not just the code comment that claimed it. **Neither worker has a test**; both existing tests mock the worker away, which is very likely why none of this was noticed. |
| 2026-08-25 | W27 | **`BULK-IMPORT-SPEC-UPDATES.md` deleted — 467 lines, of which one section was worth keeping.** The unit's premise was wrong in *both* directions. It said `BulkCreateMediaItemsCommand` exists nowhere else and should be merged out: in fact **it shipped** — command, handler, endpoint at `POST /v1/items/bulk`, and four response models — and `mediaitem.api.md` already documents it in its traceability table. The changelog's version was a stale proposal marked *"(NEW — requires MediaItem write model extension)"* with a **wrong signature** (no `OnError`/`OnDuplicate` strategies, a `MediaItemCreationRequest` type that does not exist). Merging it out would have overwritten a correct entry with an obsolete one. Its `shared/bulk-operations.md` section had *already* been applied months ago, routes corrected on the way. **Only the SQS/DLQ queue configuration was unique** — visibility timeouts (900 s / 1800 s), `maxReceiveCount: 3`, batch size 1, filter policies — now in `bulk-operations.md` with three warnings the changelog did not have: `maxReceiveCount` buys nothing while handlers swallow exceptions (**X-11.6**); batch-size-1 with a 30-minute visibility timeout means a redelivery restarts the whole job, so chunk idempotency cannot be Phase 3 work as the changelog scheduled it; and the filter values need re-checking against the naming ADR when the aggregates exist. Added a hard **⛔ none of this is built** badge to the async section, verified four ways: no worker in `src/hosts/`, both queues named only in a CDK *comment* ("add with bulk import implementation"), **zero** `bulk` entries in the authoritative projection-table manifest, and no `media-bulk-import-inputs` bucket. **`/v1/catalog/...` swept to zero** — the eight real prefixes are `/assets`, `/change-requests`, `/collections`, `/folders`, `/items`, `/profiles`, `/record-types`, `/registrations`; the two remaining textual hits are the correction notes. Two archived ADRs still carry the old spelling and were **left alone** — rewriting an archived decision record to match today's routes would falsify the history it exists to preserve. One finding in passing: **X-11.20**, a dead `MaxAssetsPerRequest` key in Catalog's config block that binds to nothing while reading as the authoritative asset cap — the second silent-fallback bug from this same pair of sections. Also corrected the Collections batch cap, listed as 100 against a real 200. |
| 2026-08-25 | W29 | **The headline reverses the unit's framing: request idempotency *does* exist.** `Magiq.AspNetCore.Idempotency` is referenced by the `Api` host, runs as **global middleware** over every write endpoint, and its table is CDK-provisioned. **Three code comments assert the opposite** ("No idempotency-key middleware exists in this platform") and all three are false. But the spec described **idempotent replay** and the middleware does **replay rejection** — repeat key → bare `409`, no body, no `ProblemDetails`, and the caller never learns the original outcome. Worse, **the key is marked *before* execution**, so a request that 500s burns its own key for 24 h. It **fails open** on absent header, unauthenticated request, or a missing tenant/owner claim. The 24 h window binds no config section and is not settable at all. **X-11.21 (High): the header is `Idempotency-Key`, not `IdempotencyKey`.** The spec, the Postman script and a code comment all had it hyphen-less, so any client following the published contract got **zero protection, silently**. A deployed, working feature that effectively nobody is using. **X-11.22 (High 🔒): the tenant claim defaults to `client_id`, not `tenant_id`** — the CDK injects the override only when set, and no env config sets it. Every `CLAUDE.md` and the spec name `tenant_id`. The compounding risk is that the idempotency middleware reads `tenant_id` independently and fails open without it, which would make idempotency inert API-wide while appearing configured. **Needs a real token to settle** — recorded as a question. *Checked and cleared while there:* `AddHeaderIdentifierProvider` cannot override the JWT (priority 200 vs 100, first non-null wins). **X-11.23 (High 🔒): the read side has no owner check.** `AssetOwnership.CheckOwner` is write-side only; no read handler returns `Forbidden` — yet both download routes advertise `403 "The caller does not own this asset."` **Any tenant member can download any asset in the tenant.** Tenant scoping itself is sound (structural, via projection key → 404 not 403). Compounded by the response being a bearer capability, and by **X-11.24**: nothing logs downloads at all — no logger, no event, no audit facility. Also **X-11.27** declared status codes are broadly wrong in both directions (unreachable 403s across ~30 routes; nine routes declaring no success code), **X-11.29** `DELETE /v1/items/{itemId}` returns 204 and re-emits forever because `Apply` never clears `ArchivedAt`, **X-11.25** nothing enforces the upload deadline and the 15-minute TTL is a compiled constant with one shared `expiresAt` across all multipart parts, **X-11.26** the ADR's 30-minute `UploadId` table does not exist, **X-11.28** a third doc comment claiming an idempotency the code contradicts. **Only two routes destroy bytes** — asset delete and multipart abort — and both are documented as such now. X-10.5 cross-noted per the unit's step 2. |
| 2026-08-25 | W22 | **The unit found a security problem, not a documentation problem.** D5 resolved *comprehensive*, so all **132** write commands were enumerated from disk (`Commands/*Command.cs` → 133 files, 1 marker interface) and classified — 132 rows, counts reconciled, so nothing was missed. Deliverable is a new file, **`shared/authorization-matrix.md`**, replacing a table that covered **6 of 132**. **86 commands have no authorization check at any layer; 66 are HTTP-reachable.** **No endpoint in the system uses `Roles()`, `Permissions()`, `Policies()` or `Claims()`** — zero across 146 endpoint classes; both hosts define an `"AuthenticatedUser"` policy and neither applies it. All enforcement that exists is 20 handler guards and 12 aggregate guards. Escalated as **X-11.30 (Critical 🔒)** rather than written up as behaviour, per the unit's own rule. **X-11.31 (Critical 🔒) is the one to fix first**: `SetCheckoutPolicy` is unguarded, and `EditSessionGuard` — the most widely applied guard in the system — is conditional on it. An unprivileged caller can disable the guard tenant-wide. Same for `SetReviewPolicy` and `SetChangeRequestPolicy`. **Privilege escalation, not a missing check**, and five small fixes cover it. **The Registration module is the clearest signal:** the five commands acting on an officer's *own* filing are guarded; the five that *decide* a filing — confirm, reject, approve/reject amendment, record submission — are not. `ApproveAmendment`'s doc comment promises a System gate that was never implemented. Also unguarded and HTTP-reachable: `PurgeMediaItemVersion` (destroys a retained record version), `WithdrawMediaItem`, all 17 Metadata commands, all 18 MediaProfile commands. Both named conflicts resolved: **Approve authorization** (roster lives on `MediaItem.ReviewSession`; both other accounts described the removed saga — Q-13 closed in W20) and **MediaProfile listing** (the read model was right; `api.md`'s owner rule never existed — corrected in two places). **One subagent claim was checked and rejected** before it reached the spec: that upload initiators let a caller name an arbitrary `OwnerId`. `UploaderId` comes from `executionContext.Actor.Id`, so the exposure is quota consumption, not impersonation. |
| 2026-08-25 | W23 | **`mediaitem.write-model.md § State Machine Interaction` written from code — G-4 closed, plus Q-6, Q-9 and Q-10.** Four of this unit's five premises were false, which is now the expected rate. **(a)** `Archive` *does* close an open edit session — `SupersedeEditSession` runs before `MediaItemArchived`, with the reason recorded in code (*"leaving it open would let a later AbandonCheckout flip an archived item back to a live status"*); no orphaned sessions exist. **(b)** `EditSessionCloseReason.Submitted` **is** emitted, by `RequestPublication` — all six members are emitted, none is dead. **(d)** `Withdraw` and `Archive` from `Revising` are legal; neither enumerates admitted statuses, so the diagram's arrows were right and the doubt was not. **Two real defects instead.** **X-11.35 (High)** — **folder assignment is guarded by nothing**: no status, archive or checkout check, and neither handler runs `EditSessionGuard`. An item can be moved while another user holds it checked out, mid-review, or **while archived** — and the archived case collides with the title reservation released at archive time. **X-11.34** — `Publish`/`Archive`/`Withdraw` skip the guard base class *and* have no aggregate editor check, so any tenant member can perform them on an item someone else holds, closing their session underneath them. The pattern is consistent: **content edits are guarded, lifecycle transitions are not.** Also found that folder assignment can **drive** the status machine via `AutoSubmitOnComplete`, which no diagram showed. **Q-9 was a spec-invented bug**: `AcceptedContentTypes` appears **nowhere in `src/`** in any revision — the field is `AllowedMediaCategories` end to end. 10 occurrences swept across five files. **Q-10**: no status constraint at assignment; `Active` is enforced once, at publish — the right seam, since assignment is cataloguing and can precede processing. **Q-6**: nine members, one enum, and `DigitalSigning` never existed (removed from four files) — but the real correction is the **consumption** side: **only 2 of 9 capabilities gate anything**. `Governance`, `Retention` and `Distribution` change nothing at all; `CheckInOut` and `Review` are governed by their policies instead. `CapabilitySet.Has(...)` has zero call sites (**X-11.37**) and Metadata keeps an unenforced parallel copy of the nine names. |
| 2026-08-25 | W24 | **Two new files — `shared/cross-aggregate-invariants.md` (15 rules) and `shared/cascade-rules.md` — closing G-2 and G-3.** The cascade answers are blunt: **only archive cascades. Deprecation and hard delete touch nothing.** That is defensible, but it was written down three different ways and mostly not at all, so *"nothing happens"* was indistinguishable from *"nobody checked"*. `domain-model.md`'s *"archiving is read-layer only — no write-side cascade"* was **false** and is corrected; `bounded-contexts.md` had it right. Also deleted `FolderDomainService` from the services table — no such class, and no folder-emptiness check exists. **The ADR turned out to be the least reliable document in the set.** `adrs/catalog-domain-invariants.md` describes a `child-folders` counter and an `active-items` counter — **neither exists** (`CounterKeys` declares exactly two) — says `ArchiveFolderHandler` *rejects* an archive when a folder has active children when it **archives them instead**, and calls the registration guard a *non-blocking warning* when it **blocks with a 422**. The shape of the error is worth noting: the ADR describes a model where a folder must be **emptied** before archiving; what shipped **archives the contents**. Opposite models, and nobody updated it when the second won. The ADR keeps the reasoning and now carries the correction table. **Six findings, two High.** **X-11.41** `FolderMediaItemsIndex` is **add-only** — no removal on archive, delete or move — so the fan-out re-archives archived items *and* **archives items the user moved out of the folder**, under their old parent. **X-11.38** deprecating a MediaProfile half-blocks its items: aggregate-loading paths refuse, index-reading paths do not, because the projector never sees the deprecation — **items stay editable and checkout-able but cannot be created or published**, a half-life nobody chose. Plus **X-11.39** depth guard bypassable by moving a subtree, **X-11.42** the assets of a deleted MediaItem can never be deleted (resolves with X-11.32), **X-11.43** a stuck counter makes a folder permanently unarchivable with no visible cause, **X-11.40** a dead index whose own comment claims it is consumed. **The truncation guard earned its keep**: it failed both new files on `unterminated-prose` before they landed — a closing bullet with no full stop. Exactly the class of damage it was written for. |
| 2026-08-25 | W25 | **`shared/consistency-model.md` written, plus a `Consistency` section on all 10 read-model files — G-6 closed and all 10 W25 warnings cleared** (29 → 19). The three answers are blunt: **staleness is unbounded, read-your-own-writes is impossible on any production path, and rebuild covers 6 of 10 aggregates.** No alarm on `ApproximateAgeOfOldestMessage` anywhere, no projector metric, no dashboard — `ProjectedVersion` could measure lag on every record and **nothing reads it for that**. RYOW fails on all four routes a client might try; the practical guidance is now written down, including that **a 404 immediately after a create is expected, not an error**. **Two findings, and the first is the significant one. X-11.44: there is no outbox.** Domain events publish to SNS after the commit, in-request — so a publish that fails leaves the event durable and **never projected**. The read model is wrong *permanently*, not temporarily; nothing retries because nothing knows. That follows from ADR-005 and **the cost was never written down** — and the platform SDK's own guidance says the opposite (*"Always use `IOutbox`"*). **X-11.45: `LastObservedAtUtc` does not exist**, zero occurrences, despite both `CLAUDE.md` files stating it as a standing convention. Every new read model is being written against a rule nobody follows. **The environment split bites here too:** dev/qa/staging project **synchronously in-request**, so lag is zero and RYOW holds *accidentally*. A staleness bug cannot be reproduced outside production, and the blue-green rebuild runbook — explicitly *"run every step against dev first"* — has only ever been exercised where lag does not exist. **Seven reference indexes cannot be rebuilt by replay at all** (fed by another module's integration events, and nothing re-emits those), and the two uniqueness counters cannot be rebuilt by anything, since they are written by command handlers rather than events. |
| 2026-08-25 | W28 | **The last unit, and its premise was false in the now-familiar way.** It named five types catalogued as value objects that carry identity and mutable state — `Reviewer`, `ReviewComment`, `RegistrationItem`, `RegistrationAmendment`, `Signer`. **Three do not exist**: there is no `Reviewer` (it is `ReviewerAssignment`), no `ReviewComment` (it is `CommentIndex`), no `RegistrationAmendment` type at all, and no `Signer` — the nearest is `SignerInfo`, an event payload record in a module with no aggregate. **So two types were misclassified, not five.** `ReviewerAssignment(ReviewerId, Decision, AssignedAt, DecidedAt?)` and `CommentIndex(CommentId, AuthorId, IsDeleted)` are **entities inside an aggregate boundary, implemented as immutable records** — both are addressed *by identifier* (`ApproveReview` finds the caller's assignment by `ReviewerId`; comments are edited and deleted by `CommentId`) and both carry state that changes while that identifier persists. Being a record is how they are stored, not what they are. **`RegistrationItem` was checked and is a genuine value object** — no mutator, never replaced after attachment, and its `MediaItemId` is a reference rather than an identity of its own. Also wrote the two **missing `Value Objects` sections** for `Collection` and `Folder` from `ValueObjects/` on disk — the last two W2 warnings, taking the board to **17, of which 16 are BI-1**. Both new sections state **"no entities"** and say why: neither aggregate holds a child list, because membership lives on the child and is read through a projected index. |
---

## 9. Appendix — what happened on 2026-08-25

Kept because the method generalises, and because the original version of this plan reached the opposite
conclusion with a shallower search.

### 9.1 The truncation, and the recovery

22 files under `docs/spec/` were damaged: **17 truncated mid-token**, 5 merely missing a trailing newline.

> **Superseded 2026-08-25 by W1.** The real figures are **23 damaged: 18 truncated mid-token, 5 merely
> missing a trailing newline.** The newline-only count is unchanged — the correction adds a *truncated*
> file, not a newline-only one. This inventory was built by searching for missing trailing newlines, and
> that is a narrower population than "files that end mid-construct": `mediaitem.read-model.md` was cut
> inside a code fence at `d0adc7bc` (2026-07-19) and **kept its newline**, the only damaged file that did,
> so it is absent from every list below. Corrected in W1, where the recovery is recorded. The rest of this
> section stands.
This plan originally stated the truncated content was unrecoverable and budgeted 3–5 days to rewrite all
17 from handlers. **That was wrong.** A full-history search recovered 15 of the 17 tails in about twenty
minutes.

The original check compared each file against the tip of each commit touching *that same path*, for three
files, and generalised. It missed two things:

1. **The wiki has its own git history.** `Media.wiki` is a repo, not a folder. Its working tree is cut in
   the same places, but earlier commits still carry complete pages.
   `RecordType-%2D-Write-Model.md` is cut at 21,595 B in the wiki working tree and **complete at 15,644 B
   in history** — that older, smaller copy is where the whole uniqueness contract came back from.
2. **A shorter revision can hold a longer tail.** The cutter truncates whatever a writing session
   produced, so a file that grew 31 KB → 44 KB can lose its ending at every size. Ranking revisions by
   size hides this; tails have to be compared, not lengths.

### 9.2 Age is what decided where each tail went

Recovery found the text. It did not make it current.

| Source | Written | Tails |
|---|---|---|
| `magiq-media` migration commit | 2026-07-07 | T2, T4, T6, T7, T8, T9, T15 |
| `magiq-media` | 2026-07-16 | T10 |
| `Media.wiki` | 2026-06-13 | T16 |
| `Media.wiki` | 2026-05-14 | T1 |
| `Media.wiki` | 2026-04-26 | T14 |
| `Media.wiki` | 2026-04-23 | T3, **T11** |
| `Media.wiki` | 2026-04-15 | T5 |
| `Media.wiki` | 2026-03-27 | T13 |

**Every wiki-sourced tail predates both the 2026-07-07 migration and the 2026-08-24 correction pass on the
file it belongs to.** What such a tail says about command dispatch, host names, routes or event names is
pre-correction *by construction*. T11 describing a MediatR `TransactionBehavior` is not a slip that
survived — it is what this repo did in April.

That split the fifteen by **what kind of claim the text makes**:

- **Age-immune — 5** (T4, T5, T13, T14, T15): link lists. Restored; all 413 relative links resolve.
- **Enumerable — 7** (T1, T2, T3, T6, T7, T8, T9): table rows naming commands, events, routes,
  projections. Restored **and checked against code** — §9.3.
- **Prose asserting behaviour — 3, 7.9 KB** (T10, T11, T16): **quarantined** to `docs/spec/_recovered/`.
  Retired by W13–W18.
- **Unrecoverable — 2** (T12, T17): marked `⚠ TRUNCATED`. W16, W17.

Also corrected: the original inventory guessed at what was behind each cut from the file's last surviving
heading, and got two badly wrong — **T1** lost one table row, not the traceability table; **T14** lost a
link list, not the Catalog relationships model. Both were rated top priority on that guess, while **T11
and T16 — the two largest real losses** — were rated middle. A cut file's last heading is not evidence of
what followed it.

### 9.3 What the code check found

| ID | Verdict |
|---|---|
| T1, T3 | ✅ verified — commands, events and routes all exist |
| T2, T6 | ✏️ routes corrected, then verified. `/v1/catalog/items/...` → `/items/bulk`; `{id}` → `{changeRequestId}` |
| T7 | ⚠️ specified, not implemented — `DocumentSigning` has no `.Endpoints` project; no signing route is served |
| T8, T9 | ⚠️ intent only — **not one** Bulk import command or projector exists; confirms drift-review **BI-1** from the spec side |

**No route in this codebase carries a `catalog` segment** — `/v1` is a FastEndpoints version group, not a
path prefix. That settles the route question for the whole tree; W27 sweeps the remainder.

**And the check found something bigger than what it was checking.** The projector names in these tables —
`MediaItemProjector`, `CollectionProjector`, `SigningSessionProjector`, `AssetProjector` — **do not exist
as classes.** The real projectors are split detail/summary/index; there are 50. The singular names appear
**88 times across `docs/spec/`** — 41 / 18 / 16 / 13 — overwhelmingly in tables nobody truncated. *(The
figure first recorded was 69, counted before the 12 tails were restored; restoring them added rows using
the same wrong names.)* Raised as **X-11.1 (High)**
in `spec-repo-drift-review.md`.

That is the recovery's real payoff, and it is not the recovered text. Checking seven old tails against
code was a pretext for reading the projection layer properly, and the spec's model of it turned out to be
wrong everywhere, not just behind the cuts.

### 9.4 The search method — so it is not run again

1. Enumerate **every blob in the object database**, not just those reachable from the current branch:
   `git rev-list --objects --all`, plus `git fsck --dangling`. Read them in one pass with
   `git cat-file --batch` — per-blob `git log --find-object` is orders of magnitude slower and is what
   made the first attempt give up early.
2. Do it in **both repos**. Seven of the fifteen recoveries came only from `Media.wiki`'s history.
3. Match **by exact path first**, then by content anchor. Basename matching alone produces false pairs —
   every context has a `context-overview.md`.
4. Compare **tails, not sizes**. For each candidate, find the longest suffix of the truncated file that
   occurs in it; whatever follows that anchor is the recovered tail.
5. For a fragment cut mid-row, grep every blob in both repos for the fragment — that is how T3's
   `BulkCreateCollectionsCommand` row was completed when no whole-file candidate matched.
6. **Date every source before trusting it.** `git log --all --format=%H\t%ad --date=short -- <path>`, then
   `git rev-parse <commit>:<path>` to find which commit wrote the blob. This is the step that moved three
   recoveries out of the spec. *(The `%2D` in wiki filenames will eat a Python `%`-format string; use
   concatenation.)*
