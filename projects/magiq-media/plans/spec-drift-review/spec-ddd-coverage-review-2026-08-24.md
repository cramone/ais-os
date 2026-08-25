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

**One unit per session.** Read this table, pick the first unblocked `☐`, work only that unit, tick it,
add a session-log line (§8). Nothing else in this document needs reading to start.

**▶ Next up: W3, W4, W13, W15, W16, W17 and W26 are all unblocked** — Stage C's salvage units need
nothing and can be taken any time. Prefer **W3 or W4** if the session is short: both are ¼ day, and W4
unblocks W10, W11 and W12 while giving every later unit somewhere to put a question it cannot settle.
**W1 landed 2026-08-25, so W2 is unblocked too** — it extends W1's workflow rather than starting one.

| ✓ | # | Unit | Size | Blocked by | Stage |
|---|---|---|---|---|---|
| ☑ | **W0** | Recover the truncated tails | — | — | *done 2026-08-25 — §9* |
| ☑ | **W1** | CI guard — no file ends mid-construct | ½ d | — | *done 2026-08-25 — found an 18th truncated file* |
| ☐ | **W2** | CI guard — required sections per file type | ½ d | W1 | A · Guard |
| ☐ | **W3** | `spec/README.md` — the question map | ¼ d | — | A · Guard |
| ☐ | **W4** | `open-questions.md` — contradiction register | ¼ d | — | A · Guard |
| ☐ | **W5** | One canonical `glossary.md` | ¾ d | W3 | B · One answer |
| ☐ | **W6** | Reconcile the architecture tier — 3 files, 3 answers | 1½ d | W3 · **D1** | B · One answer |
| ☐ | **W7** | `domain-model.md` — inventory, relationships, the rules | 1 d | W6 | B · One answer |
| ☐ | **W8** | Split `system-spec.md` | 1 d | W5, W6, W7 | B · One answer |
| ☐ | **W9** | `_Last reviewed:` + kill dangling references | ½ d | W2, W8 | B · One answer |
| ☐ | **W10** | Sweep within-file contradictions (Tier 3) | ½ d | W4, W8 | B · One answer |
| ☐ | **W11** | Integration event naming — decide, delete, ADR | ½ d | W4 · **D3** | B · One answer |
| ☐ | **W12** | Read-model table names against the CDK | ¼ d | W4, W8 | B · One answer |
| ☐ | **W13** | DDD-T11 · RecordType uniqueness contract | ½ d | — | C · Salvage |
| ☐ | **W14** | DDD-T16 · DR runbooks | ½ d | W8 | C · Salvage |
| ☐ | **W15** | DDD-T10 · MediaItem asset subscriptions | ¼ d | — | C · Salvage |
| ☐ | **W16** | DDD-T12 · ProcessingJob mirror rules | ¼ d | — | C · Salvage |
| ☐ | **W17** | DDD-T17 · `workflow_dispatch` docs | ¼ d | — | C · Salvage |
| ☐ | **W18** | Delete `docs/spec/_recovered/` | 5 min | W1, W13–W17 | C · Salvage |
| ☐ | **W19** | `sagas/` file type + `AssetIngestionSaga` | 1½ d | W3, W8 | D · Domain risk |
| ☐ | **W20** | Delete `MediaItemReviewSaga` from 4 files | ½ d | W6, W8, W19 | D · Domain risk |
| ☐ | **W21** | `DocumentSigningSaga` + the two fan-out workers | 1 d | W19 | D · Domain risk |
| ☐ | **W22** | Authorization matrix — privileged subset first | 2 d | W8 · **D5** | D · Domain risk |
| ☐ | **W23** | MediaItem's three state machines, one table | 1½ d | W2 · **D4** | D · Domain risk |
| ☐ | **W24** | Cross-aggregate invariants + cascade rules | 1 d | W7 | D · Domain risk |
| ☐ | **W25** | `shared/consistency-model.md` | ½ d | W6 | E · Consolidate |
| ☐ | **W26** | The three missing `scenarios.md` | 1 d | — | E · Consolidate |
| ☐ | **W27** | Retire `BULK-IMPORT-SPEC-UPDATES.md` | ½ d | W11 | E · Consolidate |
| ☐ | **W28** | Apply the entity-vs-VO rule | ½ d | W7 | E · Consolidate |
| ☐ | **W29** | Tier 2 client-contract sweep | 1 d | W12 | E · Consolidate |

**Blocked-by includes decisions.** A unit showing **D3**/**D4**/**D5**/**D1** is not startable until §3
records that decision as resolved, however clear its own steps look.

**≈20 days** — A 1½ · B 6 · C 1¾ · D 7½ · E 3½. Stage A is the cheapest in the plan and unblocks
everything; its four units are what stop the spec re-growing duplicates while the rest is worked.

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
| **D1** | **Authority model** — rewrite the stale architecture docs, or demote them? | **Open.** Recommendation: neither, any more. W6 merges both files into a new `architecture/bounded-contexts.md` and deletes both; W7 rebuilds `domain-model.md`. A banner was the right call when the alternative was a week of rewriting — the structure review's merge is cheaper than both. Blocks W6. |
| **D2** | ~~Truncated tails — rewrite from code, or mark and rewrite later?~~ | **Resolved 2026-08-25.** Search history first, then date what you find. 15 of 17 tails recovered: 12 restored, 3 quarantined because they predate the correction pass, 2 unrecoverable. §9. |
| **D3** | **Integration event naming** — `media.mediaitem.*` (16 uses) or `media.item.*` (12)? | **Open.** Let the code decide, then ADR it. External SNS filter policies cannot be written against both; the loser is deleted from the spec, not aliased. Blocks W11. |
| **D4** | **`Capability` enum** — API allows 4 values, write model defines 9, defaults seed 2 the API rejects. | **Open.** Recommendation: write model wins, the API list is the bug. The enum is the pivot of the activation chain and is specified nowhere. Confirm against code. Blocks W23. |
| **D5** | **Authorization matrix scope** — all ~150 commands, or the privileged subset first? | **Open.** Recommendation: privileged subset first. For a government platform the unlisted privileged commands are the risk, not the owner-scoped ones. Blocks W22. |
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
| **Projector class names do not exist, 69 spec references** | Drift review — **X-11.1**, raised 2026-08-25 by this plan's code check |
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
| ☐ | Extend W1's workflow: match file by name pattern, assert required `##` headings present. |
| ☐ | `<agg>.write-model.md` → `Purpose` · `Invariants` · `Properties` · `Value Objects` · `Status transitions` · `Methods (Commands)` · `Domain Events` · `Handler-side Pre-conditions` · `Published Integration Events` · `Consumed Integration Events` · **`State Machine Interaction`** *(required only where the aggregate has more than one state machine — MediaItem has three; W23 delivers it)*. |
| ☐ | `<agg>.read-model.md` → `Read Models` · `Projection Handlers` · `Queries` · `Read Model Types` · `Consistency`. |
| ☐ | `<agg>.api.md` → `API Conventions` · `Authorization` · `Write Endpoints` · `Read Endpoints` · `Command → Event → Projection Traceability` · `Related`. |
| ☐ | `<agg>.scenarios.md` → `Index` · `Diagram Key` · ≥1 scenario · `Related`. |
| ☐ | `context-overview.md` → `Purpose` · `Responsibilities` · `Aggregate List` · `Service Boundaries` · `High-Level Event Flows` · `Integration Event Contracts` · `Related Specifications`, plus **fail if a `Ubiquitous Language` heading is present** — that section belongs to `glossary.md`. **Ship this one rule as a warning until W5 lands**, or it fails 6 of 7 overviews on day one for work nobody has done yet. |
| ☐ | `sagas/<saga>.md` → `Purpose` · `Correlation Key` · `State Table` · `Transition Table` · `Timeouts` · `Compensation` · `Idempotency` · `DLQ & Poison Policy` · `Manual Intervention Runbook`. |
| ☐ | Every file → `_Last reviewed:` line. **Warn, don't fail, until W9 lands** — 72 files lack it today. |
| ☐ | Expect failures on day one and record them: 3 aggregates have no `scenarios.md` (W26); **no** `Consistency` section exists anywhere (W25); `Folder` has no `Value Objects` (W28); `mediaitem.write-model.md` has no `State Machine Interaction` (W23); 6 context overviews still carry `Ubiquitous Language` (W5, warned not failed). That list *is* the backlog, and it should match the board. |

**Done when.** The check runs on every `docs/**` PR, and every failure it reports maps to a `☐` on the
board — no unexplained red. It is not expected to be green until Stage E closes.

**Touches.** `.github/workflows/`.

---

#### W3 · `spec/README.md` — the question map · ¼ d · needs nothing

**Goal.** The highest-value file in this plan and the cheapest. Not an index of files — an index of
*questions*, with a **"Not"** column naming the file people wrongly open.

**Read first.** `reviews/spec-structure/…-2026-08-25.md § 3`.

| ✓ | Step |
|---|---|
| ☐ | Create `docs/spec/README.md`: one table, *question → the one file that answers it → not this one*. |
| ☐ | Cover at minimum: term definitions · which context owns X · what commands an aggregate accepts · what a route does · how a long-running process ends · how stale a read can be · what is still contested · what has been decided and why (→ `docs/adrs/`, a sibling of `docs/spec/`, not inside it). |
| ☐ | Point rows at files that do not exist yet (`glossary.md`, `open-questions.md`, `consistency-model.md`, `sagas/`) and mark them **planned**. A map that shows the gaps is more useful than one that hides them, and it stops the next person inventing a home. |
| ☐ | Link it from the repo `CLAUDE.md` § *Spec and architecture — source of truth*. |

**Done when.** Someone who has never opened this spec can find the owner of any of the 16 dimensions in
one hop.

**Touches.** `docs/spec/README.md`, `CLAUDE.md`.

---

#### W4 · `open-questions.md` — contradiction register · ¼ d · needs nothing

**Goal.** Give a known-unresolved disagreement somewhere to live **in the repo**. They currently
accumulate in review documents on `Z:\`, which per the repo's own `CLAUDE.md` is Chase's machine only —
**Estelle and Akshay cannot see the list of things the spec is wrong about.**

**Read first.** `reviews/spec-structure/…-2026-08-25.md § 5`; the DDD review's §5 contradiction register.

| ✓ | Step |
|---|---|
| ☐ | Create `docs/spec/open-questions.md`: `#` · question · sides · status · owner · opened. |
| ☐ | Seed it from the DDD review's Tier-1 contradictions — integration event naming (D3), `Capability` enum (D4), Approve authorization specified three ways, MediaProfile owner-scoped listing (security-relevant), read-model table naming. |
| ☐ | State the closing rule in the file: **an entry closes by being deleted**, with the winning rule written into the owning file. No "resolved" section — that is how a register becomes a second spec. |
| ☐ | Add a row to `spec/README.md`'s table pointing at it. |

**Done when.** Every Tier-1 contradiction is visible to someone with only repo access, and each names an
owner.

**Touches.** `docs/spec/open-questions.md`, `docs/spec/README.md`.

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
| ☐ | **First repair `system-spec.md`'s corrupted table at ~line 1103** — it breaks mid-cell into a duplicate OpenSearch field table, so the largest glossary being merged is itself incomplete. Mid-file, so no truncation marker helps; the glossary simply stops. |
| ☐ | Create `docs/spec/glossary.md`: term · definition · owning context · first introduced. Merge all 8 sources; where two disagree, the aggregate spec wins over the architecture tier. |
| ☐ | Add every term the 2026-08 corrections introduced that no glossary has: `EditSession`, `ReviewSession`, `OriginStatus`, `ConformanceGap`, `Alias`, `CompiledMetadataTemplate`, `SuppressedFieldNames`, `AllowsConcurrentEdit`, `VersionArtifact`, tier-policy, the saga state names, and `Job` / `Batch` / `Phase` / `Chunk`. |
| ☐ | Delete all 8 source sections. Context overviews link to the glossary; none defines terms. |
| ☐ | Do **not** put the glossary in the wiki. It is generated from `docs/`, lags it, and per `CLAUDE.md` should not be hand-edited — a glossary living downstream of the spec cannot be the spec's authority. |

**Done when.** `grep -rl 'Ubiquitous Language' docs/spec | grep -v glossary.md` returns nothing. If W2
has already landed, flip its context-overview rule from warn to fail; if not, W2 ships it as fail from
the start.

**Touches.** `glossary.md` (new), `system-spec.md`, `domain-model.md`, 6 × `context-overview.md`.

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
| ☐ | Merge into `architecture/bounded-contexts.md`, `service-boundaries.md` as the base — it is five months newer and already corrects the other. |
| ☐ | **Do not carry over** `bounded-context.md`'s duplicate aggregate inventory, event catalogue, queue table or host list. Three inventories disagreeing 9 / 10 / 12 is two too many; the host list is stale per X-1.1. The aggregate inventory's single home is `domain-model.md` (W7). |
| ☐ | Assign a **relationship type to all 12 context relationships**, not just the 5 external ones. The 7 internal contexts appear in `system-spec.md` with no shared-kernel / conformist / partnership / ACL designation at all. |
| ☐ | Absorb `system-spec.md § Cross-Context Relationships` here (W8 will expect it gone from there). |
| ☐ | **`system-architecture.md` is the third answer, and no other unit touches it.** Its `## Services` section enumerates **twelve** numbered services — `### 1. Ingest API` … `### 12. Storage tier` (`:80`–`:401`) — against the nine real hosts. That is where the "8 vs 9 vs 12" of X-1.1 comes from. Reconcile it against `src/hosts/` and `service-boundaries.md`, or delete the section and link. |
| ☐ | Note that `### 6. SecuredSigning Adapter` and both Bulk workers are specified-not-built — `service-boundaries.md` already says so for SecuredSigning; BI-1 says so for the Bulk workers. |
| ☐ | Delete the dangling `specs/media-management-domain-spec.md` reference at `bounded-context.md:598` **before** deleting the file — **that file has never existed**, and `domain-model.md` cites it as the authority. (W7 removes the twin reference in `domain-model.md`'s header.) |
| ☐ | Delete **both** source files. Sweep inbound links for **both** names — `grep -rl bounded-context.md docs/` **and** `grep -rl service-boundaries.md docs/`. The merge deletes `service-boundaries.md` too, and both W25 and the drift review link to it; sweeping only the obvious one leaves half the links dangling. |

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
| ☐ | **The single aggregate inventory** lives here. Reconcile the 9 / 10 / 12 disagreement against `src/modules/` and state the count with its source. |
| ☐ | **Cross-aggregate relationship model** — currently nowhere. Which aggregate references which, and in which direction. |
| ☐ | **State the reference-by-id rule once, explicitly.** It is implied everywhere and stated nowhere. |
| ☐ | **State the one-aggregate-per-transaction rule** — and justify the one genuine exception (event append + name reservation), which is described but never defended. See X-9.6, which found the same seam from the code side. |
| ☐ | **Name the entity-vs-VO rule.** Applying it is W28; here just state the test. |
| ☐ | Absorb `system-spec.md § Naming Conventions` (W8 expects it gone). |
| ☐ | Delete the dangling `specs/media-management-domain-spec.md` reference from this file's own header at `domain-model.md:5` — **that file has never existed**, and this file cites it as its authority. (W6 removes the twin reference at `bounded-context.md:598` before deleting that file.) |

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
| ☐ | Multi-Tenancy · Authentication & Authorization → `shared/multi-tenancy-and-auth.md` |
| ☐ | Concurrency · Idempotency · Cross-Aggregate Constraint Enforcement → `shared/concurrency-and-consistency.md` |
| ☐ | Event Sourcing Mechanics · Messaging Patterns · Storage Boundaries · S3 Upload Patterns → `shared/event-store-and-messaging.md`. **Not `persistence-and-eventing.md`** — `docs/adrs/persistence-and-eventing.md` already exists, and two files one directory apart sharing a basename is how the wrong one gets opened. Check the other four names against `docs/adrs/` before creating them. |
| ☐ | Saga Coordination Patterns → `shared/saga-patterns.md` — the cross-cutting rules only; individual sagas get their own files in W19. |
| ☐ | Infrastructure · Observability · **Disaster Recovery** · CORS · Rate Limiting → `shared/operations.md`. **The DR section is the one still truncated** — move what survives; W14 completes it in its new home. |
| ☐ | Cross-Context Relationships → already moved by W6. Ubiquitous Language → already moved by W5. Naming Conventions → already moved by W7. Verify all three are gone rather than duplicated. |
| ☐ | **Delete `system-spec.md`.** Do not leave a stub — a file that survives as a stub is one somebody writes into again. Update every inbound link; there are many. |
| ☐ | Carry the `⚠ TRUNCATED` marker into `shared/operations.md` with the DR section, so W14's target is still marked. |

**Done when.** `system-spec.md` does not exist, no link points at it, and all 19 sections are findable
from `spec/README.md` — 15 in the five new `shared/` files, 3 already relocated by W5/W6/W7, and the
Table of Contents discarded.

**Touches.** 5 new `shared/` files, `system-spec.md` (deleted), inbound links across `docs/`.

---

#### W9 · `_Last reviewed:` + kill dangling references · ½ d · needs W2, W8

| ✓ | Step |
|---|---|
| ☐ | Add `_Last reviewed: YYYY-MM-DD_` to every spec file. Undated files are why nobody can tell which side of the drift review a claim sits on — 5 carry no date header at all, including `api-conventions.md` and `security-scenarios.md`. |
| ☐ | Use the file's last substantive edit date, not today's, or the line means nothing. |
| ☐ | Sweep for links to files deleted in W5–W8 and to `specs/media-management-domain-spec.md`. |
| ☐ | Flip W2's `_Last reviewed:` check from warn to fail. *(This is why W9 is blocked on W2 as well as W8.)* |

**Done when.** W2 is fully failing-strict and green.

**Touches.** all of `docs/spec/`.

---

#### W10 · Sweep within-file contradictions (Tier 3) · ½ d · needs W4, W8

**Goal.** The contradictions a merge or a banner does not reach — two claims inside one file.

| ✓ | Step |
|---|---|
| ☐ | `MediaItemStatus` membership. |
| ☐ | `ITenanted` vs `ITenantScoped` — spec side only; the platform SDK defines `ITenantScoped`. |
| ☐ | Projector count · bucket count. |
| ☐ | `FailureCategory` wire values that would throw on `Enum.Parse`. |
| ☐ | Anything unresolvable in one sitting → `open-questions.md` (W4), not a TODO comment. |

**Done when.** Every Tier-3 contradiction in the DDD review's §5 is resolved or registered in
`open-questions.md`. *(Tier 1 is not this unit's — those are W4, W11, W12, W22 and W23.)*

**Touches.** various.

---

#### W11 · Integration event naming — decide, delete, ADR · ½ d · needs W4 · **D3**

| ✓ | Step |
|---|---|
| ☐ | Read the `*IntegrationEventPublisher` classes for what is **actually published**. Code decides; the spec does not get a vote. |
| ☐ | Delete the losing scheme from every spec file. **Do not alias** — external SNS filter policies cannot be written against both. |
| ☐ | Write the ADR. |
| ☐ | Close the entry in `open-questions.md`. |

**Touches.** spec files carrying either scheme, `docs/adrs/`, `docs/spec/open-questions.md`.

---

#### W12 · Read-model table names against the CDK · ¼ d · needs W4, W8

| ✓ | Step |
|---|---|
| ☐ | `media-*-detail` vs `media-*` — resolve against `cdk-magiq-media`, the only physical truth. `system-spec.md` contradicts itself here: `:674` is under *Storage Boundaries* and `:990` under *Infrastructure Overview*, so after W8 the two halves live in **different files** — `shared/event-store-and-messaging.md` and `shared/operations.md`. Fix both. |
| ☐ | Close the entry in `open-questions.md`. |

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
| ☐ | Rewrite the transaction and conflict-handling prose: the source describes a MediatR `TransactionBehavior` and `NameReservationConflictBehavior`; **this repo dispatches via `ICommandDispatcher` and does not use MediatR**. |
| ☐ | Confirm — do not assume — the `IRecordTypeUnicityService` body, the `RECORDTYPE` scope key, and the per-operation reservation intents (`Reserve` / `Swap` / `Release`). These are the parts most likely to have survived four months intact, which is exactly why they need checking. |
| ☐ | Check the Published / Consumed Integration Events tables against the actual publisher. |
| ☐ | Move the corrected text into `recordtype.write-model.md`, delete its `⚠ TRUNCATED` marker, delete the `_recovered/` file. |

---

#### W14 · DDD-T16 · DR runbooks · ½ d · needs W8

**Read first.** `docs/spec/_recovered/system-spec.DDD-T16.md` (3,299 B, written 2026-06-13);
`cdk-magiq-media`; drift-review X-1.1.

| ✓ | Step |
|---|---|
| ☐ | Re-map five phantom Lambdas — `Media.Api`, `Media.QueryApi`, `Media.Projectors.Lambda`, `Media.SagaOrchestrator.Lambda`, `Media.Processing.Lambda`, **none of which exist** — to the real hosts: `Api`, `QueryApi`, `Projectors.ReadModel`, `Projectors.Search`, `EventConsumers`, `ProcessingWorker`, `SagaOrchestrator`, `TimeoutScanner`. `cdk-magiq-media` is authoritative for deployed function names and aliases. |
| ☐ | The Backup Verification Schedule table is **cut mid-cell in the source too** — the only recovery that came back incomplete. Finish it from the CDK, or cut it. |
| ☐ | Write into `shared/operations.md` (W8's destination), not into the deleted `system-spec.md`. |
| ☐ | Delete the marker and the `_recovered/` file. |

---

#### W15 · DDD-T10 · MediaItem asset subscriptions · ¼ d · needs nothing

**Read first.** `docs/spec/_recovered/mediaitem.write-model.DDD-T10.md` (1,124 B, 2026-07-16 — the
freshest of the three); AssetManagement domain events.

| ✓ | Step |
|---|---|
| ☐ | One name, two answers: the tail says `AssetUploaded`; the surviving text above the cut attributes the same fields to `AssetUploadInitiated`. AssetManagement's events are the arbiter. |
| ☐ | Decide whether the `media-change-requests` reference-model section — present in wiki blob `ba9bce72`, **deliberately never restored** — belongs in this file. If yes it needs `Resolved` / `Abandoned`, not `Approved` / `Rejected`. Overlaps W20. |
| ☐ | Move in, delete marker, delete `_recovered/` file. |

---

#### W16 · DDD-T12 · ProcessingJob mirror rules · ¼ d · needs nothing

**Target.** `docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md` — cut at
`Mirrors current job statu`. **Nothing survives to work from**; every revision in both repos cuts at the
same token.

| ✓ | Step |
|---|---|
| ☐ | Write the read-model mirror rules from the real projectors: `ProcessingJobDetailProjector`, `ProcessingJobSummaryProjector`. **There is no `ProcessingJobProjector`** — see X-11.1. |
| ☐ | Delete the `⚠ TRUNCATED` marker at the end of the file. |

---

#### W17 · DDD-T17 · `workflow_dispatch` docs · ¼ d · needs nothing

**Target.** `docs/spec/architecture/branching-and-deployment.md` — cut at `` `workflow_di ``. **Nothing
survives to work from**; the single prior revision cuts identically and the page was never published to
the wiki.

| ✓ | Step |
|---|---|
| ☐ | Write the manual-dispatch trigger documentation from `.github/workflows/build-and-push.yml`. |
| ☐ | Cross-check against `cdk-magiq-media` — the deploy trigger is a commit into that repo's `config/<env>.json`, not `repository_dispatch`. |
| ☐ | Delete the marker. |

---

#### W18 · Delete `docs/spec/_recovered/` · 5 min · needs W1, W13–W17

| ✓ | Step |
|---|---|
| ☐ | Delete the folder, README included. |
| ☐ | Remove W1's `_recovered/` exclusion and W1's mid-construct allowlist — with all five markers gone, the guard should be unconditional. |

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
| ☐ | Establish the file type at `contexts/<Ctx>/sagas/<saganame>.md`. Owning context = the one that owns the **outcome**; `AssetIngestionSaga` → AssetManagement. Cross-context sagas get a link from each participating `context-overview.md`. |
| ☐ | Write `contexts/AssetManagement/sagas/assetingestionsaga.md` to W2's contract: `Purpose` · `Correlation Key` · `State Table` · `Transition Table` · `Timeouts` **with their config keys** (today the spec says only "Video = 4h, others shorter") · `Compensation` · `Idempotency` · `DLQ & Poison Policy` · `Manual Intervention Runbook`. |
| ☐ | **Specify the bypass-branch exit.** A bypassed asset emits neither `ProcessingJobSucceeded` nor `ProcessingJobFailed` — the only two closure triggers listed — so the fast-exit branch **has no stated way to end**. This is a live behavioural hole, not a documentation gap: confirm against the handlers whether the saga actually terminates, and if it does not, that is a **code** finding, not a spec one. |
| ☐ | Cross-cutting, into `shared/saga-patterns.md`: correlation-id scheme, retry budget, DLQ policy, runbook conventions. |
| ☐ | Add the `sagas/` row to `spec/README.md`, marked live rather than planned. |

**Done when.** The production saga has a file, and the transition table has no row that cannot be reached
or exited.

---

#### W20 · Delete `MediaItemReviewSaga` from 4 files · ½ d · needs W6, W8, W19

**Goal.** A saga specified four ways that **does not exist**. *(D6 resolved: this plan owns it, not the
drift review.)*

| ✓ | Step |
|---|---|
| ☐ | Delete from `bounded-context.md:624` *(gone after W6 — verify it did not survive the merge)*, `domain-model.md:317-319`, `system-architecture.md:293,322,337`, `system-spec.md:885` *(→ wherever W8 put it)*. |
| ☐ | `ChangeRequests/context-overview.md` (2026-08-23) is the reconciled version: **the direction is inverted.** Catalog emits `MediaItemApprovedIntegrationEvent`; ChangeRequests' own handler dispatches `ResolveChangeRequestCommand`. No saga. |
| ☐ | `system-spec.md:885` additionally specified it over `ChangeRequestApproved` / `ChangeRequestRejected` — **events the write model does not have.** It has `Resolved` / `Abandoned`. Fix wherever else those names appear. |

---

#### W21 · `DocumentSigningSaga` + the two fan-out workers · 1 d · needs W19

| ✓ | Step |
|---|---|
| ☐ | `DocumentSigningSaga` — spec as **design, not as shipped**: the code is deferred, `DocumentSigning` has no `.Endpoints` project, and nothing deploys `SagaOrchestrator.DocumentSigning`. Say so in the file. |
| ☐ | Give it the correlation key it has never had — the spec offers `SigningSessionId`, `MediaItemId` and `EnvelopeId`. One timeout value instead of three, with its config key. |
| ☐ | **The two process managers nobody calls sagas:** `CollectionArchiveFanOutWorker` and `IFolderArchiveFanOutWorker` have no failure, retry, partial-completion or resume spec. **A half-archived subtree currently has no compensation and no status surface.** Spec both to the same contract. |
| ☐ | If a fan-out worker turns out to have no resume path in code, that is a code finding — file it. |

---

#### W22 · Authorization matrix — privileged subset first · 2 d · needs W8 · **D5**

**Goal.** `system-spec.md § Command-Level Authorization` covers **6 of ~150 commands**. For a government
platform, the unlisted privileged ones are the risk.

| ✓ | Step |
|---|---|
| ☐ | Rebuild **from code** — endpoint attributes plus handler guards. Not from the spec. |
| ☐ | Privileged first: `ForceReleaseCheckout`, `ExpireCheckout`, every `actor.ActorType == "System"` path, every Processing and Bulk command. All currently unlisted. |
| ☐ | Then the long tail, or enumerate and date what is left. |
| ☐ | Resolve **Approve authorization**, specified three ways — reviewer-scoped / System-only / `ReviewSession` roster — across `system-spec.md:147` *(→ `shared/multi-tenancy-and-auth.md` after W8)*, `security-scenarios.md:123`, `error-catalog.md:297`. |
| ☐ | Resolve **MediaProfile listing**: `mediaprofile.api.md:41` documents an owner-scoped check on `caller.owner_id`; `mediaprofile.read-model.md:223` says that query never existed and **every profile in the tenant is returned to every caller**. Confirm against code, then fix whichever side is wrong. |
| ☐ | **Anything the code does not enforce stops being a spec task** — it becomes a security finding with its own urgency. Escalate immediately rather than filing it. |

---

#### W23 · MediaItem's three state machines, one table · 1½ d · needs W2 · **D4**

**Goal.** Status × edit-session/checkout × folder-assignment. Each machine is specified alone; their
interaction is defined nowhere. One table closes a dozen open questions at once.

| ✓ | Step |
|---|---|
| ☐ | Add the interaction matrix to `mediaitem.write-model.md` under the `State Machine Interaction` heading W2 expects. |
| ☐ | Answer explicitly, in that table: does `Archive` close an open `EditSession`? What raises `EditSessionCloseReason.Submitted` — the value exists and no method sets it? Can a non-editor `Publish` / `Archive` / `Withdraw` an item another user holds? Is `Withdraw` / `Archive` legal from `Revising` — the diagram has the arrow, the methods do not list the state? |
| ☐ | Fix the `Capability` enum per **D4** and give it a specified home in `mediaprofile.write-model.md`. It is the pivot of the activation chain and is specified nowhere; the API allows 4 values, the write model defines 9, and the defaults seed 2 the API rejects. |
| ☐ | Resolve asset status on role assignment — "any status" vs "must be `Active`". |
| ☐ | Resolve the write/read seam: `AcceptedContentTypes` is written, `AllowedMediaCategories` is read. Clients hit this directly. |

---

#### W24 · Cross-aggregate invariants + cascade rules · 1 d · needs W7

| ✓ | Step |
|---|---|
| ☐ | `shared/cross-aggregate-invariants.md` — one catalogue. E.g. "a Registration's MediaItem must be Published"; "a Folder cannot be archived with active registrations in its subtree". These currently live in `adrs/catalog-domain-invariants.md`, **outside the spec tree, in a folder for decisions rather than rules**. |
| ☐ | Leave the ADR in place as the decision record it is; move the *rules* out of it and link back. |
| ☐ | `shared/cascade-rules.md` — one table. Today `domain-model.md` says "archiving is read-layer only — no write-side cascade" while `bounded-context.md` *(→ merged into `architecture/bounded-contexts.md` by W6)* describes a fan-out job that archives the whole subtree. Check what survived the merge before assuming the contradiction is still live. |
| ☐ | Undefined everywhere, decide each: what happens to **Assets** when a MediaItem is archived; to **Registrations** when a Folder is archived; to **MediaItems** when a MediaProfile is deprecated. |

---

### Stage E · Consolidate

#### W25 · `shared/consistency-model.md` · ½ d · needs W6

**Goal.** Projection *mechanics* are well documented. **Policy does not exist.**

| ✓ | Step |
|---|---|
| ☐ | Create `shared/consistency-model.md`: read-your-own-writes rule; projection-lag bound or SLO — `api-conventions.md` alludes to "a client that reads a lagging projection" and gives **no figure**; rebuild procedure. |
| ☐ | Cover the reference indexes that **cannot be rebuilt by aggregate replay** — stated at `service-boundaries.md:133` *(→ `architecture/bounded-contexts.md` after W6)*. That is the case where the policy actually bites. |
| ☐ | Add the `Consistency` section W2 requires to each `<agg>.read-model.md`: lag class + RYOW behaviour, linking here. |

---

#### W26 · The three missing `scenarios.md` · 1 d · needs nothing

| ✓ | Step |
|---|---|
| ☐ | `Folder/folder.scenarios.md` — **does not exist and never has** *(history-checked 2026-08-25: no blob in either repo at any revision; genuinely greenfield)*. Folder's two highest-risk behaviours — archive cascade and cross-collection subtree move — have **no worked example anywhere**. |
| ☐ | Add the Folder-owned scenarios to `Catalog/business-scenarios.md` so the hole is visible if it reopens. |
| ☐ | Both Bulk import scenarios — coordinate with drift-review BI-1/BI-2 rather than duplicating. `BulkMediaImportWorker` is a five-phase process manager across three modules, spec'd with no compensation, no timeout and no dedup rule. Mark them intent, per the code check. |

---

#### W27 · Retire `BULK-IMPORT-SPEC-UPDATES.md` · ½ d · needs W11

| ✓ | Step |
|---|---|
| ☐ | Merge out `BulkCreateMediaItemsCommand` and the SQS/DLQ configuration — **they exist nowhere else.** |
| ☐ | **Delete the file.** It is an unmerged changelog in imperative future tense sitting in `aggregates/`, and it prescribes `/v1/catalog/...` routes — confirmed 2026-08-25 that **no route in the codebase carries a `catalog` segment**. |
| ☐ | Same sweep for any other `/v1/catalog/...` left in the spec. |

---

#### W28 · Apply the entity-vs-VO rule · ½ d · needs W7

| ✓ | Step |
|---|---|
| ☐ | Apply W7's rule: `Reviewer`, `ReviewComment`, `RegistrationItem`, `RegistrationAmendment` and `Signer` all have identity and mutable state but are catalogued as value objects. |
| ☐ | `Folder` has **no `Value Objects` section at all** — W2 fails on it. |

---

#### W29 · Tier 2 client-contract sweep · 1 d · needs W12

| ✓ | Step |
|---|---|
| ☐ | Status codes · route spellings · part-URL TTL · bulk batch caps · download authorization · delete semantics. |
| ☐ | Idempotency: the spec claims it exists — **this plan owns that claim**; drift-review X-10.5 owns the OpenAPI half. Coordinate, note in both. |

---

## 6. Exit criteria

Deliberately checkable, not aspirational. Every criterion names the unit that delivers it; every unit
appears against at least one criterion.

| ✓ | Criterion | Unit |
|---|---|---|
| ◑ | No file in `docs/spec/` ends mid-construct, and **CI fails if one does** — *CI half done 2026-08-25 (W1); closes fully at W18, when the five marked exceptions and the `_recovered/` exclusion go and the guard becomes unconditional* | W1, W18 |
| ☐ | Every file type satisfies its required-sections contract, enforced in CI and green | W2 + everything it fails on |
| ☐ | `spec/README.md` answers "which file owns this question" for all 16 dimensions | W3 |
| ☐ | Every contradiction still open is visible **in the repo**, with an owner | W4 |
| ☐ | **One glossary**, containing every term the 2026-08 corrections introduced; no other file defines terms | W5 |
| ☐ | **One file answers context ownership and one answers the host inventory** — the 8 / 9 / 12 disagreement is gone, every context relationship has a type, and `bounded-context.md` and `service-boundaries.md` are both deleted with no inbound links | W6 |
| ☐ | **One aggregate inventory**, and the reference-by-id + one-aggregate-per-transaction rules are stated once | W7 |
| ☐ | `system-spec.md` does not exist; all 19 of its sections are findable from `spec/README.md`, and no new `shared/` file shares a basename with a `docs/adrs/` file | W8 |
| ☐ | Every spec file carries `_Last reviewed:`, and no link points at a deleted file | W9 |
| ☐ | **Every question has one answer** — for each Tier-1 and Tier-3 contradiction, exactly one document states the rule and the others link to it or are deleted | W10 (T3) · W4, W11, W12, W22, W23 (T1) |
| ☐ | One integration-event naming scheme survives in the spec, with an ADR; the loser is deleted, not aliased | W11 |
| ☐ | Read-model table names match the CDK | W12 |
| ☐ | `docs/spec/_recovered/` does not exist and no `⚠ TRUNCATED` marker survives | W13–W18 |
| ☐ | **Every saga and process manager has an owning file** to the W2 contract — including the two fan-out workers that are process managers without the name | W19, W21 |
| ☐ | No spec file references `MediaItemReviewSaga` | W20 |
| ☐ | **Every privileged command's authorization is stated**, with the long tail enumerated and dated | W22 |
| ☐ | MediaItem's three state machines have one interaction table, and `Capability` has a specified home | W23 |
| ☐ | **Cascade and cross-aggregate invariants are stated once**, in the spec tree rather than in an ADR | W24 |
| ☐ | A projection-lag bound and a read-your-own-writes rule exist, and every read model states its lag class | W25 |
| ☐ | Every aggregate has a `scenarios.md`; Folder's archive cascade and subtree move have worked examples | W26 |
| ☐ | `BULK-IMPORT-SPEC-UPDATES.md` is gone and nothing it uniquely held was lost | W27 |
| ☐ | The entity-vs-VO rule is stated **and applied** — no entity catalogued as a value object | W7, W28 |
| ☐ | Tier 2 client-contract items resolved; the spec no longer claims idempotency support it does not have | W29 |
| ☐ | *(Drift review, not closed by this plan)* No traceability table names a class that does not exist | **X-11.1** |

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
