---
id: MM-041
type: plan
project: magiq-media
workstream: domain-flow
consumes: [MM-040]
depends-on: []
blocked-by-external: []
status: done
todo-id: 5fc762ca-dc8a-58ed-94bb-f7f99f670129
branches: []   # TODO: record the branch Chase pushed 2026-09-14 — see § Session log
ado: -
created: 2026-09-13
---

# Domain flow remediation — DF-1 … DF-4 · **spec and ADRs only**

_Consumes [`reviews/domain-flow/domain-flow-review-2026-09-13.md`](../../reviews/domain-flow/domain-flow-review-2026-09-13.md)
(MM-040). **Owns the four new findings only.** DF-5 … DF-18 stay with the workstreams that already hold
them — MM-025/MM-026, MM-030/MM-035, MM-032, MM-038 and the drift review — and are not tracked here._

**Shape: spec and ADR first, code staged behind each decision.** These are design errors, not code-vs-spec
drift, so there is nothing to bring back into line — the corrected design has to be written down before it
can be built. Three of the four cannot have spec text written at all until a call is taken, so Phase 0 is
decisions and everything else is gated on it.

> ## ⛔ Scope narrowed 2026-09-14: this plan ends at the spec
>
> **Phase 4 — the code — was dropped, and it has no owner.** Chase's call: this plan delivers the corrected
> design and stops there. Phases 0–3 are the whole of it.
>
> **What that leaves true of the running system.** The spec now describes the corrected design; **the code
> still has every defect MM-040 found**, and nothing here changes that:
>
> - **DF-1** — a **successful** registration still locks its folder permanently. `media.registration.confirmed`
>   reaches no consumer, `Confirmed` has no successor in code, and the `active-registrations` counter is
>   never released on the happy path. `FolderHasActiveRegistrations`, forever, with no route to clear it.
> - **DF-2** — `media-registration-item-ref` still never learns an item was withdrawn or deleted, so a new
>   legal filing can be opened against a withdrawn item.
> - **DF-3** — the `RequiredForEdit` gate is still checked once, at checkout, and is still voidable
>   mid-edit. The landed change is still recorded as `Abandoned`.
> - **DF-4** — unbuilt either way; `RetentionSchedule` does not exist.
>
> **This is a deliberate, recorded gap, not an oversight** — the same treatment DF-8/9/14/15 get below. The
> design is settled and written down, so whoever picks the code up is not re-deciding anything; they are
> reading § Definition of done and the spec files it names.
>
> ⚠ **It has now been scoped out once. The note under § Not in scope applies to this too: it should not be
> scoped out twice.**

---

## The frame: DF-1 and DF-2 are the same defect twice

Worth stating before the units, because it changes what "done" means.

`catalog-domain-invariants.md` § Hierarchy Invariants states the design intent for the archive guard, and
it is the right intent:

> the counter is a **Catalog-owned projection of Registration facts** rather than a synchronous call into
> that context

The defect is not the mechanism. **It is that the projection consumes three of the six facts.**
`active-registrations` moves on `initiated`, `rejected` and `cancelled`; `confirmed`, `submitted` and
`resubmitted` reach nothing (DF-1). DF-2 is the identical shape pointed the other way: Registration's own
`media-registration-item-ref` consumes three of Catalog's MediaItem events — `created`, `approved`,
`archived` — and `withdrawn` and `deleted` reach nothing.

Both reference models are correct on the paths someone tested and wrong on a path nobody enumerated. So
the unit that actually closes them is not two handlers; it is **a completeness rule for cross-context
reference projections** plus the two handlers that rule exposes. Without the rule the next reference model
has the same hole, and there are already seven of them (`consistency-model.md` § What replay cannot
rebuild), none with a rebuild path.

**One more thing DF-1 pulls in.** `catalog-domain-invariants.md` records `FolderRegistrationIndex` /
`RegistrationCountIndexProjector` as live dead code that **"write on every registration event"** and that
nothing reads — X-11.40, currently filed as a cleanup call ("Delete the projector, the index and the
table, or wire the guard to it"). DF-1 makes it a correctness call: the dead index already sees the fact
set the live counter is missing. **X-11.40 must be decided as part of D1, not separately** — deleting it
while the counter is the guard forecloses the cheaper of the two fixes.

---

## Landed 2026-09-13, ahead of Phase 0

Two corrections that needed no decision, done before the phases open because both were factually wrong
rather than undecided.

- **`ActiveChangeRequestId` deleted from `domain-model.md`.** The field does not exist —
  `mediaitem.write-model.md` § Properties lists `ReviewSession` and `ActiveSigningSessionId` and nothing
  between them, and both `mediaitem.api.md` and `mediaitem.read-model.md` said so. Replaced with the
  **id-custody chain**, which Phase 2 depends on: `EditSessionOpened.ChangeRequestId?` → copied to
  `ReviewSession.EditSessionChangeRequestId?` at submission → carried on `MediaItemPublicationRequested`
  and `MediaItemApproved` → out on `MediaItemApprovedIntegrationEvent` to `ReviewChangeRequestCloser`.
  **The copy is the load-bearing step**: the edit session closes at submission, so without it nothing on
  the item still names the request the work was done under. D2 has to reason about that chain.
- **`domain-model.md`'s duplicated aggregate detail removed** — the `## Aggregate detail` section (~420
  lines) and the `## Value Objects` table, replaced by a pointer table. Its header claimed it owned three
  things and it owned far more; the surplus is what kept going stale. Four stale entries were found in one
  pass: the module table's `MediaChangeRequest`, the VO table's `MediaChangeRequestId`, the MediaItem
  table's `ActiveChangeRequestId`, and **DF-10's `ProcessingJob` contradictions** — wrong creation trigger,
  four events against Processing's seven, no `Bypassed`, no recovery path. That last one is now moot as a
  *documentation* finding: the contradicting copy is gone, and Processing's own spec is the only account.
  **DF-10's substantive question — whether `ProcessingJob` should be an aggregate at all — is untouched.**

---

## Phase 0 — the four decisions. **All four taken 2026-09-14 (Chase).**

| | Decision | Taken |
|---|---|---|
| **D1** | What `active-registrations` means, and X-11.40 with it | **A — "under obligation."** Counter stays raised on `confirmed`; a new terminal `Discharged` state past `Confirmed` releases it. **X-11.40 → delete** the projector, index and CDK table |
| **D2** | Is the `RequiredForEdit` gate a real invariant | **A — make it real.** Checked at checkout, submit and publish; request bound to item and `kind`; `Kind` stored; reference row carries `Status`/`Scope`/`Kind` |
| **D3** | What happens to the two shipped `Retention` fields | **Sequence the gate behind the migration**, per tenant. `Retention` becomes a publish gate for a tenant only after its record types finish the two-cycle retirement |
| **D4** | Six retention triggers or four | **Six, with the two missing timestamps in the same change** — `SupersededAt` on the version row, and a reachable `POST /close`. If they slip, gate the two at *authoring* time; never ship them inert |

**Phases 1–3 are complete** — every unit landed in `mgq-magiq-media\docs\`. See § Session log.

The option sets and their costs are preserved below, because the rejected options are the reasoning.

---

### The calls, as they were put

Written as calls, with the option set and what each costs. Following `pending-decisions/` (MM-031): these
need a decision, not more research. The evidence is in MM-040 and in the files cited per row.

### D1 · Critical — What does `active-registrations` mean?

The counter guards `ArchiveFolder` and it currently means *"has an in-flight filing"*. The rule
`cross-aggregate-invariants.md` rule 13 is trying to express is *"is this item under a retention
obligation"* — and a **confirmed** filing is the strongest case of that, not the absence of one. It cannot
mean both, and today it silently means neither: over-counts on success (DF-1), under-counts on
reject→resubmit→confirm (R-2, already documented).

| Option | What it costs |
|---|---|
| **A — "under obligation".** Counter stays raised on `confirmed`; folder stays locked while a filing is live. Needs a decrement path that today does not exist, because `Confirmed` is terminal and uncancellable (`registration.scenarios.md` R-5) | A new terminal transition on `Registration` — revocation/discharge — which is a real domain concept the aggregate is missing anyway (DF-17). Largest, and arguably the correct model |
| **B — "in flight".** Decrement on `confirmed`; archive is not blocked by a completed filing | One handler. But it means archiving a folder holding live statutory registrations is permitted, which is exactly the outcome the ADR says the coupling exists to prevent |
| **C — wire the guard to `FolderRegistrationIndex`** instead of the counter. The projector already writes on every registration event | Closes DF-1 and X-11.40 together and needs no new counter semantics. But it moves a **write-side invariant onto a projection**, which `folder.write-model.md` states twice is the wrong basis for one, and the ADR chose counters over projections deliberately |

**Recommendation: A, with B's handler as the mechanism.** The obligation reading is what a records
authority would expect, and the missing discharge transition is a gap worth closing on its own terms.
**Decide X-11.40 in the same call** — under A or B the index is deletable; under C it is load-bearing.

### D2 · High — Is the `RequiredForEdit` change-request gate a real invariant?

Today it is checked once, in `CheckOutMediaItemHandler`, against a request that can be abandoned the next
second, with nothing binding the request to the item or its `kind`, and validation that fails open on
absence (DF-3).

| Option | What it costs |
|---|---|
| **A — make it real.** Re-check at submit/publish, bind request → item → kind, and decide what `Abandon` does to a checkout that cites the request | Touches `MediaItem`, `ChangeRequest` and the ADR. The hard sub-call is abandon: refuse it while referenced, or let it force-close the edit session |
| **B — delete it.** Remove `ChangeRequestPolicy` / the `RequiredForEdit` branch | Honest, cheap, and consistent with how the platform already treats seven of nine capabilities. Loses a governance claim the product may be selling |
| **C — downgrade it to advisory.** Record the request id on the session, gate nothing, say so | Cheapest. But a gate that reads as enforcement and is not is the failure mode `editing-lifecycle-and-concurrency.md` already warns about for the edit lock |

**Recommendation: A or B, not C.** A gate that fails open in a compliance product is worse than no gate,
because a reader assumes the guarantee. If A, note it lands next to DF-8's finding that `ReviewPolicy` is
also pinned and also read by nothing — same defect, same aggregate, worth one pass.

### D3 · High — What happens to the two shipped `Retention` fields?

`metadata-schema-composition.md` § Decision 2 records that `Retention` ships contributing
`retention_expiry_date` and `retention_disposal_action`.
`retentionschedule.design-decisions.md` makes it a pure publish gate. § *What this deliberately does not
settle* names three open items and **the migration is not one of them** (DF-4).

The call: what becomes of those two fields, the values items already hold under them, and existing
`Retention` profiles whose next republish is now refused for a schedule that cannot yet be authored.

Note the shape of the retirement, because it is what makes this non-trivial: per
`recordtype.write-model.md` a published field is retired by `DeprecateField` → publish → `RemoveField` →
publish. **Two publish cycles per affected record type**, and per DF-15 dropping a field from the compiled
template can re-key its collision partner on items already created.

**Recommendation:** sequence the gate behind the migration, not with it. `Retention` should not become a
publish gate on a tenant's profile until that tenant's items have somewhere for the two field values to
go.

### D4 · Medium — Ship all six retention triggers, or only the four that resolve?

`retentionschedule.design-decisions.md` states the rule — *"a retention trigger must name an event the
platform raises and timestamps"* — then rules **"Ship all six and gate the two on their register rows"**,
where `Superseded` needs a `SupersededAt` that does not exist and `Closure` needs a required `ClosedDate`
that per DF-18 **cannot be populated over HTTP**.

The argument for six is sound in isolation: widening an enum pinned into immutable versions is the change
the design exists to avoid. The cost is that immutable versions can be written containing rules that were
never computable. `Closure` additionally cannot resolve for an item with no folder, and folder assignment
is optional at creation with no invariant preventing the pin.

**Recommendation: ship all six, and add the two missing timestamps in the same change** — `SupersededAt`
on the version row, and a reachable `POST /close` (DF-18) — so no version can be authored against a
trigger the platform cannot resolve. If the timestamps slip, gate the two members at *authoring* time
rather than shipping them inert.

---

## Phase 1 — DF-1 + DF-2 · gated on D1 — ✅ **complete 2026-09-14**

Do these together. They are one defect (see § The frame) and splitting them means writing the same
convention twice.

| # | Unit | ✓ | Landed as |
|---|---|---|---|
| 1.1 | Completeness rule | ✅ | `cross-aggregate-invariants.md` § Completeness of cross-context reference projections — the rule, the two hazards (X-4.15 allowlist drift; synchronous projections below prod), and § And there is no repair path |
| 1.2 | Apply to `active-registrations` | ✅ | Rule 13 § *what `active-registrations` counts, per producing event* (7 rows) · `Registration/context-overview.md` § Outbound rewritten with a per-event counter column · `mediaitem.write-model.md` § Consumed Integration Events, all seven accounted for |
| 1.3 | Apply to `media-registration-item-ref` | ✅ | `registration.write-model.md` § Consumed Integration Events — every Catalog MediaItem event, `withdrawn`/`deleted` added, "no write" rows stated, plus § Repair position |
| 1.4 | Correct rule 12's guarantee | ✅ | Rule 12 ⚠ note · `registration.scenarios.md` R-4 — *"`Published` means `IsPublished` on the reference row, not `MediaItemStatus`"* |
| 1.5 | Record the discharge transition | ✅ | `registration.write-model.md` — `Discharged` appended as the 8th status, § *`Confirmed` is no longer the end of the line*, properties, invariants, method, `RegistrationDischarged` event, command, 7th integration event · `registration.api.md` `POST /discharge` · `context-overview.md` payload contract · R-5 corrected · two new error codes. **Half of DF-17 closed with it** (revocation); reference-correction stays with the drift review |
| 1.6 | Update the ADR | ✅ | `catalog-domain-invariants.md` § Decision — counts obligation; *which fact set the projection consumes*; X-11.40 resolved to delete |
| 1.7 | State the repair position | ✅ | `consistency-model.md` § What this costs when a reference model's rules change — two acceptable closes, and silence is not one |

<details>
<summary>Original unit descriptions</summary>

| # | Unit | Files |
|---|---|---|
| 1.1 | **Write the completeness rule for cross-context reference projections.** Every reference model must enumerate the producing context's *full* event set and state, per event, either the write it makes or an explicit reason it makes none. No silent omissions | New section in `docs/spec/shared/cross-aggregate-invariants.md`, alongside § Write-side reference indexes |
| 1.2 | **Apply it to `active-registrations`.** State all six Registration integration events and each one's effect on the counter, per D1 | `docs/spec/shared/cross-aggregate-invariants.md` rule 13 · `docs/spec/contexts/Registration/context-overview.md` § Outbound · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` (`RemoveRegistrationRefCommand`, § Consumed Integration Events) |
| 1.3 | **Apply it to `media-registration-item-ref`.** State every Catalog MediaItem integration event and its effect, including `withdrawn` and `deleted` | `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md` § Consumed Integration Events · `docs/spec/contexts/Registration/context-overview.md` |
| 1.4 | **Correct rule 12's guarantee.** `registration.scenarios.md` R-4 asserts *"`Published` means `MediaItemStatus.Published` — post-approval"*, which is false for any item that was published and then withdrawn. Fix the scenario and the rule together | `docs/spec/shared/cross-aggregate-invariants.md` rule 12 · `registration.scenarios.md` R-4 |
| 1.5 | **Record the discharge transition** if D1 = A. `Registration` needs a terminal state past `Confirmed` that releases the obligation. Fold in DF-17's neighbouring gap (no route to correct a mistyped `Reference` or record a revocation) if it comes cheap | `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md` § Status transitions · `registration.scenarios.md` R-5 · `docs/spec/architecture/domain-model.md` § `Registration` |
| 1.6 | **Update the ADR.** The intent sentence is right; the section needs to say which fact set the projection consumes and why, and resolve X-11.40 per D1 | `docs/adrs/catalog-domain-invariants.md` § Hierarchy Invariants (Uniqueness Counters) |
| 1.7 | **State the repair position.** Neither counter can be rebuilt (`consistency-model.md`), so a spec change alone leaves every already-confirmed registration's counter wrong. Either specify a seeding pass — the ADR already notes *"pre-existing resources need a one-off seeding pass"* — or record that no production data exists yet and the point is moot | `docs/spec/shared/consistency-model.md` § What replay cannot rebuild |

> **1.7 is the one most likely to be skipped and shouldn't be.** Under D1=A/B the semantics change, which
> means every existing counter value is wrong under the new reading, and nothing recomputes it.

</details>

## Phase 2 — DF-3 · gated on D2 — ✅ **complete 2026-09-14**

| # | ✓ | Landed as |
|---|---|---|
| 2.1 | ✅ | `editing-lifecycle-and-concurrency.md` § The `RequiredForEdit` gate is a real invariant, checked three times |
| 2.2 | ✅ | `mediaitem.write-model.md` § Handler-side Pre-conditions — two new check points + the three-bindings section · `changerequest.write-model.md` § `Kind` becomes stored |
| 2.3 | ✅ | `changerequest.write-model.md` § `Abandon` is never refused for being in use · `ChangeRequests/context-overview.md` § Responsibilities and § How a change request reaches a checkout |
| 2.4 | ✅ | `changerequest.scenarios.md` CRC-1 — checkout *leans* open; submit and publish fail closed |
| 2.5 | ✅ | Rule 10 rewritten · reference row carries `Status`/`Scope`/`Kind` · the closer's swallow narrowed to `Resolved` only · `ChangeRequestNotForItem` / `ChangeRequestWrongKind` added to `error-catalog.md` |

> **One sub-call went against the plan's lean, deliberately: `Abandon` is *not* refused while referenced.**
> Unit 2.3 offered "refused while referenced" as the likely answer. Refusing needs ChangeRequests to hold a
> **reverse** reference index of Catalog's live sessions — an eighth cross-context projection with no rebuild
> path, carrying a write-side invariant on eventually-consistent data. That is the option **D1 had just
> rejected** for the archive guard, hours earlier in the same pass, so taking it here would have been
> incoherent. The refusal moved to Catalog's submit/publish checks instead: no new index, the *"dispatches no
> command at another aggregate"* boundary intact, and the error in front of the person doing the governed
> work. Recorded in the ADR with the rejected option.

<details>
<summary>Original unit descriptions</summary>

## Phase 2 — DF-3 · gated on D2

| # | Unit | Files |
|---|---|---|
| 2.1 | State the decision and its reasoning in the ADR | `docs/adrs/editing-lifecycle-and-concurrency.md` § ChangeRequest as a governance container |
| 2.2 | If D2 = A: specify the re-check points, and the binding of request → item → `kind`. `changerequest.write-model.md` currently says *"`kind` is derived, not stored, and nothing enforces it"* and *"This aggregate imposes no cardinality at all"* — both have to change or the gate stays unenforceable | `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` § Handler-side Pre-conditions · `docs/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.write-model.md` § Properties, § Status transitions |
| 2.3 | If D2 = A: specify what `Abandon` does to a live checkout citing the request. Today: nothing, and the context *"dispatches no command at another aggregate"* — which may be the right boundary, in which case the answer is that `Abandon` is refused while referenced | `changerequest.write-model.md` · `docs/spec/contexts/ChangeRequests/context-overview.md` § Responsibilities |
| 2.4 | Fix the fail-open. `changerequest.scenarios.md` CRC-1: *"Validation **fails open on absence**"* | `docs/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.scenarios.md` CRC-1 |
| 2.5 | Make `Resolved` and `Abandoned` distinguishable to Catalog, or state why a boolean is sufficient. Today the index stores `IsOpen` only, so the closer's swallow (`ChangeRequestNotOpen` → success at Information) is invisible | `docs/spec/shared/cross-aggregate-invariants.md` rule 10 · `ChangeRequests/context-overview.md` |
| 2.6 | If D2 = B: delete `ChangeRequestPolicy` from the profile, its event, its route and the rule-10 row — and check DF-8's `ReviewPolicy` in the same pass | `mediaprofile.write-model.md` § Capability Enum · `cross-aggregate-invariants.md` rule 10 |

## Phase 3 — DF-4 · gated on D3, D4 — ✅ **complete 2026-09-14**

| # | ✓ | Landed as |
|---|---|---|
| 3.1 | ✅ | `retentionschedule.design-decisions.md` § The migration off the two shipped fields — a section of its own, with the five-step per-tenant sequence |
| 3.2 | ✅ | Same file, § The gate activates per tenant, behind the retirement · `metadata-schema-composition.md` § The two shipped fields, and the order of operations |
| 3.3 | ✅ | § The two missing timestamps ship with the vocabulary — `SupersededAt` on the version row and `POST /v1/folders/{folderId}/close` with a required `closedDate` body · `folder.write-model.md` D-11 note rewritten. **DF-18 closed with it** |
| 3.4 | ✅ | § `Closure` on an item with no folder — *undeterminable, reported*; the pin-time invariant rejected, with why |
| 3.5 | ✅ | `mediaprofile.write-model.md` capability table — `Retention` is ⏳, not ❌, with the ✅-designed / ❌-built distinction spelled out |

> **The DF-15 hazard is called out inside the migration**, not left to be rediscovered: deprecating a
> colliding `retention_*` field re-keys its collision partner on items already created. Step 4 says check for
> collision partners first, and sequence per record type rather than in bulk.

<details>
<summary>Original unit descriptions</summary>

## Phase 3 — DF-4 · gated on D3, D4

| # | Unit | Files |
|---|---|---|
| 3.1 | Add the migration to the design doc as a first-class section. It currently has *"What this deliberately does not settle"* naming three items; the migration belongs there or in a section of its own | `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md` |
| 3.2 | Sequence the gate behind the migration per D3 — state that the `Retention` publish gate activates per tenant only after that tenant's record types have completed the two-cycle field retirement | same file · `docs/adrs/metadata-schema-composition.md` § Decision 2 |
| 3.3 | Record the D4 outcome on the trigger table, and if the timestamps are in scope, specify `SupersededAt` on the version row and a reachable `POST /close` | `retentionschedule.design-decisions.md` § `trigger` · `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md` § Status transitions (D-11) |
| 3.4 | Settle `Closure` for unfoldered items — either an invariant that a `Closure`-triggered schedule cannot be pinned to a profile whose items may be unassigned, or an explicit "undeterminable, reported" case | `retentionschedule.design-decisions.md` § `trigger` · `docs/spec/architecture/domain-model.md` § MediaItem assignment lifecycle |
| 3.5 | Reconcile the `Retention` row in the capability table — it reads `Nothing behavioural ❌` today and the design makes it a gate | `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md` § Capability Enum |

## ~~Phase 4 — code~~ · **dropped 2026-09-14, unowned**

**This plan ends at Phase 3.** The code that would make the corrected design real was dropped from scope by
Chase and has **no owner** — the same treatment DF-8/9/14/15 get under § Not in scope, and recorded here
rather than deleted so the next reader knows the gap is deliberate.

**The four defects are all still live in the running system.** See § Scope narrowed at the top of this file
for what specifically remains true. The short version: a successful registration still locks its folder
permanently, a withdrawn item can still be freshly registered, and a governed edit can still publish under
an abandoned change request.

Two facts worth keeping for whoever eventually takes it on, because both were learned the hard way and
neither is re-derivable from the spec:

- **The consumer allowlist is hand-maintained.** `ConsumerRegistrations` and `[MessageType]` in the CDK's
  `sqs-queues.ts` are two lists with *"nothing enforcing the match"* (**X-4.15**). Every fix here adds a
  handler, and one without its allowlist entry **silently never delivers** — which is the mechanism of DF-1
  and DF-2 themselves, and of X-4.18. **The app repo alone is not enough**; `mgq-magiq-media-infra` has to
  be in scope for any of this work.
- **None of it is reproducible outside production.** Projections are synchronous in dev/qa/staging, so a
  missing consumer behaves correctly on every tier a developer can reach. Tests have to assert **the
  subscription**, not the outcome.

**What the spec now gives that session:** the design is settled, so nothing is re-decided. The corrected
per-event tables, the `Discharged` transition, the three-point gate and the retention sequencing are all
written down and cross-referenced, and § Definition of done names the files.

Two standing hazards from the review that apply to every unit here:

- **The consumer allowlist is hand-maintained.** `changerequest.write-model.md`: *"a hand-maintained
  mirror of `ConsumerRegistrations` with nothing enforcing the match"* (X-4.15). Every Phase 4 unit adds a
  handler, and adding one without its `[MessageType]` in `sqs-queues.ts` **silently never delivers** —
  which is precisely the failure mode DF-1 and DF-2 already are. A drift check here is cheap insurance and
  arguably belongs in unit 1.1.
- **None of this is reproducible outside production.** Projections are synchronous in dev/qa/staging
  (`consistency-model.md` § Environment divergence), so a missing consumer behaves correctly on every tier
  a developer can reach. Integration tests have to assert the subscription, not the outcome.

---

## Definition of done

| | Condition | State |
|---|---|---|
| 1 | Phase 0's four decisions recorded — ADRs for D1/D2/D3, design doc for D4. A decision that lives only in this plan is not recorded | ✅ `catalog-domain-invariants.md` · `editing-lifecycle-and-concurrency.md` · `metadata-schema-composition.md` · `retentionschedule.design-decisions.md` |
| 2 | The completeness rule (1.1) exists in `cross-aggregate-invariants.md` and **both** reference models are restated against it, every producing event accounted for | ✅ |
| 3 | `registration.scenarios.md` R-4 and R-5 no longer assert guarantees the model does not make | ✅ |
| 4 | `mediaprofile.write-model.md`'s capability table agrees with the retention design about what `Retention` does | ✅ |
| 5 | Every spec edit lands in a PR against `mgq-magiq-media` — spec changes are code-reviewed in the same PR as the change they describe. **`docs/` is the only copy**, so a spec change reaches readers only through the repo | ✅ **Pushed 2026-09-14 (Chase).** A **docs-only** PR: the normal rule that spec rides with its code cannot apply, because the code is unowned |
| 6 | `reviews/README.md` MM-040 moves off `Draft`, and MM-041 gets a terminal outcome here | ✅ MM-040 was already `done`/`plan`; MM-041 → **`done`** 2026-09-14 |

**All six conditions met. This plan is closed.** Phase 4 is not part of it, so the design *is* the whole of
it, and nothing under `docs/` is now known to be wrong about DF-1…DF-4.

> ⚠ **Done means this plan delivered what it scoped — not that DF-1…DF-4 are fixed.** The corrected design
> is written down and reviewable; **the defects are still live in the running code and have no owner.** See
> § Scope narrowed. A reader who takes `status: done` as "the registration bug is closed" has read it wrong,
> which is why that section sits at the top of the file rather than in a footnote.

---

## Session log

### 2026-09-14 — Phases 0–3 complete; Phase 4 dropped and unowned

**Phase 0's four decisions were taken by Chase**: D1 = A (obligation, + `Discharged`, X-11.40 → delete),
D2 = A (make the gate real), D3 = sequence the gate behind the migration, D4 = six triggers with the two
missing timestamps. Phases 1, 2 and 3 then landed in full — **15 files** under
`D:\source\github\sprbrk-standard\mgq-magiq-media\docs\`, across 4 ADRs and 11 spec files.

**Three things worth carrying forward:**

1. **Several things the spec describes as built are not, and the spec is the side that stands.** Decided
   2026-09-14 (Chase) when this came up: **the spec is the target; where source does not match it, source
   moves.** So these are Phase 4 work items, not drift to reconcile, and no git archaeology is needed.

   Found while scoping Phase 4 by reading source rather than spec:

   | Specified as built | Actually in the tree |
   |---|---|
   | `MediaItemWithdrawnIntegrationEvent`, published by `MediaItemDomainEventMapper` | **Neither the contract nor the mapper case.** The *domain* event exists and projects internally |
   | The ChangeRequests lifecycle — `Resolve`, `Abandon`, `ChangeRequestResolved`/`Abandoned`, Catalog's `ChangeRequestLifecycleEventHandler`, `ReviewChangeRequestCloser` | **None of it.** Only `Create`, the three comment commands, and `ChangeRequestCreatedIntegrationEvent` |

   **Two consequences worth carrying.** The withdrawn event has **two** waiting consumers, not one —
   Registration's reference model (DF-2) *and* the ChangeRequests comment-thread close, which is therefore
   **inert today whatever the CDK allowlist says**, so both land with the producer (unit 4.2). And unit 4.6
   builds `Status`/`Scope`/`Kind` onto a reference index whose lifecycle events do not exist yet, which is
   why it is sized Medium rather than "add three columns".

   `MediaItemDeletedIntegrationEvent` **is** present and published with no subscriber, exactly as DF-2
   describes — which is why **unit 4.3 is the starting point**.

   The wider lesson is MM-040's own framing: it is **spec-only by declaration** — *"No code was read"* — so
   every finding states what the spec says, not what is built. Legitimate for a review, and exactly why
   Phase 4 sizes against source.
2. **The `Abandon` sub-call went against unit 2.3's lean**, deliberately and for a stated reason — see the
   note under Phase 2. It is recorded in the ADR with the rejected option, not silently.
3. **D1 bought a gap closed rather than a workaround.** The `Discharged` transition required by the
   obligation reading is the same transition **DF-17** says `Registration` is missing for recording a
   revocation. Half of DF-17 closes with it; reference-correction stays with the drift review. **DF-18 also
   closed**, via D4's reachable `POST /close`.

**Phase 4 was then dropped entirely and left unowned** (Chase, 2026-09-14), narrowing this plan to spec and
ADRs. It was first not-started — the session had no shell and `mgq-magiq-media-infra` was not connected, so
writing the app half alone would have shipped handlers that silently never deliver — and then scoped out on
the call that this workstream is spec work. **The four defects remain live in the code with no owner**; see
§ Scope narrowed.

### 2026-09-14 — closed

**Chase pushed the docs-only PR; MM-041 → `done`.** All six conditions in § Definition of done are met and
MM-040 was already `done`/`plan`, so the workstream's spec side is complete and the pair is matched.

**What closing does not mean.** The code for DF-1…DF-4 is unowned and the defects are live. `done` here is
"this plan delivered the corrected design", not "the registration bug is fixed".

**Two bookkeeping items this session could not do**, both needing a shell:

- `branches:` is still `[]` — the pushed branch name was never recorded here. The cycle gate wants at least
  one branch on a `done` plan; fill it in.
- **No Control Tower card comment was written** for any part of this work — `cycle.comment(...)` needs the
  shell. This log is the only record. Run it against MM-041 when one is available.

## Not in scope

DF-5 … DF-18. Their homes, unchanged:

| Findings | Owner |
|---|---|
| DF-7 (archive cascade's two contracts) | MM-025 / MM-026 — X-11.17 open |
| DF-5, DF-6 (derived state, no reconciler) | MM-032 `projection-rebuild/`, parked. **Start at divergence detection, not a rebuild tool** — its own advice |
| DF-11, DF-16 (idempotency, orphan contracts) | MM-030 / MM-035 `event-reliability/` |
| DF-12 (signing mutual exclusion) | MM-038 `document-signing/`, parked. **Worth reading before that module is built, not after** — it is a design fault, not an implementation gap |
| DF-8, DF-9, DF-14, DF-15 (the pinned-vocabulary seam) | **No owner.** MM-040 argues they are one problem and will not converge if fixed separately. Candidate for the next workstream once this one lands |
| DF-10, DF-13, DF-17, DF-18 | The drift review |

> **DF-8/9/14/15 being ownerless is the gap this plan leaves open on purpose.** It was scoped out to keep
> MM-041 shippable; it should not be scoped out twice.
>
> **As of 2026-09-14 there are two ownerless gaps, not one** — DF-8/9/14/15, and **the code for DF-1…DF-4**,
> dropped with Phase 4. They are different in kind and the difference matters when either is picked up:
> DF-8/9/14/15 still need the *argument* made, while DF-1…DF-4's design is settled and written down and only
> the implementation is missing. **The second is the cheaper one to resume and the more urgent one to
> resume** — its defects are live in a compliance-grade product today, where the pinned-vocabulary seam is
> still a design question.

**Two of the out-of-scope findings closed anyway, as a by-product of D1 and D4** — recorded so the drift
review does not re-work them:

| Finding | What closed it |
|---|---|
| **DF-17**, the `Registration` third — *"no route to … record that the authority revoked the filing"* | D1's `Discharged` transition. **Only that third**: correcting a mistyped `Reference` and detaching a document attached in error are untouched, as are the `MediaItem` and `ChangeRequest` instances |
| **DF-18** — `Folder.Close` carries retention semantics and cannot be reached | D4's reachable `POST /close` with a required `closedDate`. `ArchivedDate` is the same defect on the neighbouring endpoint and stays with D-11 |
