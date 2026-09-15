---
id: MM-040
type: review
project: magiq-media
workstream: domain-flow
raised-by: []
status: done
outcome: plan
todo-id: 3d6eb9fb-9fbf-5c65-97b7-6a7050802830
created: 2026-09-13
---

# Domain flow review — where the model breaks when you follow it end to end

_Scope: `docs/spec/` read as a whole, tracing each lifecycle from first command to terminal state and
across every context boundary it crosses. **Authorization and authentication are out of scope by
instruction** — nothing here is a guard, claim or role finding._

_Spec only. No code was read. Every claim cites the spec file that makes it, and where two spec files
disagree, both are cited._

---

## The verdict, up front

The per-aggregate models are good. **The failures are all at the joins**, and they cluster into four
shapes that recur across every context:

1. **Derived cross-aggregate state that is written once and never reconciled.** `CollectionId` on
   descendants, `MediaItem.RegistrationIds`, the `active-registrations` counter, the `depth` counter,
   `FolderMediaItemsIndex`. Each is maintained by a subset of the events that should move it, none has a
   reconciliation job, and per `consistency-model.md` § What replay cannot rebuild **none of them can be
   rebuilt**. Divergence here is permanent by construction, not eventually-consistent.

2. **Write-side invariants enforced against read-side projections.** `folder.write-model.md` states the
   correct rule twice — *"a projection, and so the wrong basis for an invariant"* — and then the
   registration guard, the checkout gate, the profile-policy gate and the asset-status gate all break it.

3. **Terminal states reached before the irreversible act, or without the compensating one.** The archive
   cascade publishes `CollectionArchived` before it knows whether the cascade can succeed. The signing
   saga writes `Bypassed`/links the session after the envelope has already gone to real signers. Both are
   the same ordering mistake.

4. **Events published with no consumer, and consumers with no producer.** Ten-plus published contracts
   with nothing subscribed, against a wire format nobody validates. In two cases the *missing* consumer is
   what makes a happy path corrupt state (DF-1, DF-2).

Below, ranked. **DF-1 through DF-4 are new.** The rest largely restate or generalise findings already
tracked as X-11.x / MM-025 / MM-030 / MM-032 — noted per row so this review does not re-open closed work.

---

## DF-1 🔴 — A successful registration permanently blocks folder archival. This is the happy path.

**New. Not tracked anywhere I can find.**

The `active-registrations` counter is the sole gate on `ArchiveFolder`
(`cross-aggregate-invariants.md` rule 13). Its two writers:

> `RegistrationInitiatedIntegrationEvent` | **Catalog** — `RegistrationInitiatedEventHandler` dispatches
> `AddRegistrationRefCommand` … incrementing its active-registration counter
> `RegistrationRejectedIntegrationEvent` … `RemoveRegistrationRefCommand`
> `RegistrationCancelledIntegrationEvent` … `RemoveRegistrationRefCommand`
> — `Registration/context-overview.md` § Outbound

And the third terminal event:

> `RegistrationConfirmedIntegrationEvent` | **Nothing in this repo.**

`Confirmed` is terminal and uncancellable — `registration.scenarios.md` R-5: *"A `Confirmed` registration
cannot be cancelled at all."* So the counter is incremented on initiation and, on the **successful** path,
is never decremented by anything, ever.

**Consequence:** every folder containing a media item with a confirmed registration becomes permanently
unarchivable, with `FolderHasActiveRegistrations`. Not for the retention period — forever, and with no
route to clear it, because the counter is written by command handlers and per `consistency-model.md`
*"no replay of any kind reproduces them"* and *"No tool does this."* The collection path then makes it
worse in the opposite direction: it has no registration guard at all and archives the parent anyway
(rule 13's ⚠ note, X-11.17), so the same fact yields "blocked forever" at folder level and "silently
archived" at collection level.

**The modelling error underneath:** "does this item have a live filing?" is being answered by a counter
that tracks *open* registrations, while the domain rule the guard is trying to express is *"is this item
under a retention obligation"* — and a confirmed filing is the strongest case of that, not the absence of
one. Either the counter must decrement on `confirmed` (making the guard mean "in flight"), or the guard
must read registration state rather than a counter. It cannot mean both.

**Related known leak in the other direction** (`registration.scenarios.md` R-2, already documented):
reject → resubmit → confirm leaves the item with *no* ref and the counter one short. So the same counter
over-counts on success and under-counts on retry.

---

## DF-2 🔴 — Registration's own reference model never learns an item was withdrawn or deleted

**New.**

`registration.write-model.md` § Consumed Integration Events lists exactly three inbound events —
`MediaItemCreated`, `MediaItemApproved`, `MediaItemArchived`. Catalog publishes more:

> `MediaItemDeletedIntegrationEvent` — **Published with no subscriber**
> — `mediaitem.write-model.md` § Published Integration Events

`MediaItemWithdrawnIntegrationEvent` has no Registration handler either. `MediaItem`'s lifecycle
explicitly includes `Published → Withdrawn → Draft` (`domain-model.md` § MediaItem status lifecycle).

So `media-registration-item-ref.IsPublished` stays `true` after a withdrawal, and rule 12
(*"only … for a **published** MediaItem"*) is enforced against a stale flag. `registration.scenarios.md`
R-4 reasons carefully about the archive case — *"an archived item is refused too because archiving clears
the same flag"* — and does not notice that withdrawal clears nothing.

**Consequence:** a new legal filing can be opened against an item that has been withdrawn from
publication, or a withdrawn/deleted item can be attached as a supporting document to a live filing. For a
regulated-records product this is the wrong direction of failure — the guard exists precisely to stop it.

---

## DF-3 🔴 — `ChangeRequestPolicy` is checked once, at checkout, and can be voided mid-edit

**New.**

`RequiredForEdit` is enforced by exactly one handler:

> `IChangeRequestQueryService.IsOpenAsync` | Blocking — `ChangeRequestNotOpen` | Runs whenever a change
> request was supplied — `mediaitem.write-model.md`, `CheckOutMediaItemHandler` only

`ChangeRequest.Abandon` is reachable from `Open` at any time, is terminal, has no reopen, and the context
dispatches nothing at `MediaItem` (*"**Out of scope:** MediaItem state, edit locks … This context
dispatches no command at another aggregate"* — `ChangeRequests/context-overview.md`).

So: check out under `cr-01`, abandon `cr-01`, keep editing, submit, publish. The governance requirement is
satisfied by a request that no longer exists, and nothing in either context can observe it. Then at
approval the closer swallows the mismatch — *"treats `ChangeRequestNotOpen` and `ResourceNotFound` as
success and logs at Information"* — so the change that actually landed is recorded permanently as
**Abandoned**, and Catalog's index cannot even tell the difference: *"That index stores a **boolean
`IsOpen`**, so `Resolved` and `Abandoned` are indistinguishable to Catalog."*

**Compounding:** nothing binds the named request to the item or to its `kind`.
`changerequest.write-model.md` is explicit — *"`kind` is derived, not stored, and nothing enforces it
… **This aggregate imposes no cardinality at all**"* — and `changerequest.scenarios.md` CRC-1 says
validation *"fails open on absence"*. The stated rule *"only a `governance` request may be named on a
checkout"* is therefore unenforceable: any open request id satisfies the gate for any item.

---

## DF-4 🟠 — The `Retention` capability's meaning is being redefined under items that already carry its fields

**New.**

`retentionschedule.design-decisions.md` (accepted 2026-09-03) makes `Retention` a publish gate:
*"A profile carrying the `Retention` capability must pin a `RetentionScheduleRef` before it may publish."*

But `metadata-schema-composition.md` § Decision 2 records what shipped: *"the capability as actually
shipped contributes **two** fields, not four (`retention_expiry_date` and `retention_disposal_action`)."*

The design does not say what becomes of those two fields, of the items already holding values under them,
or of existing `Retention` profiles whose next republish is now refused for a schedule that cannot yet be
authored. Given `recordtype.write-model.md`'s own retirement rule (`DeprecateField` → publish →
`RemoveField` → publish), that is a two-cycle migration per affected record type, unmentioned.

Two smaller fits worth settling before it ships:

- **Half the trigger vocabulary names timestamps that do not exist.** The same file states the rule — *"a
  retention trigger must name an event the platform raises and timestamps"* — then rules *"Ship all six and
  gate the two on their register rows"*, where `Superseded` *"needs a `SupersededAt`"* and `Closure`
  *"needs a required `ClosedDate`"*. Pinning an enum into immutable versions is the whole point of the
  design; shipping members whose backing timestamp does not exist writes uncomputable rules into immutable
  versions.
- **`Closure` is unresolvable for unfoldered items.** Folder assignment is optional at creation
  (`domain-model.md`: *"Unassigned is a **creation-time-only** state"*), and no invariant prevents pinning
  a `Closure` schedule to a profile whose items may never enter a folder.

---

## DF-5 🟠 — Two counters and one index back write-side invariants and are structurally unrepairable

*Generalises X-11.39, X-11.41, X-11.43 and MM-032; recorded here because the three are one problem.*

| State | Written by | Never moved by | Guard it backs |
|---|---|---|---|
| `active-registrations` | `Add`/`RemoveRegistrationRefHandler` | `registration.confirmed` (DF-1) | `FolderHasActiveRegistrations` |
| `depth` | `CreateFolder`, `MoveFolder` (moved node only) | descendants on a subtree move | `DepthExceeded` |
| `FolderMediaItemsIndex` | `MediaItemCreated` only | archive, delete, **move** | archive fan-out traversal |

`cross-aggregate-invariants.md` § Stated but not enforced is blunt about the third — *"it **archives items
that have since been moved to a different folder**, under their old parent"* — and about the reverse:
an item assigned to a folder *after* creation is never in the index, so a retention-locked record is
archivable forever and the run still reports `IsComplete`.

`consistency-model.md` closes the loop: the counters *"cannot be rebuilt at all"*, the seven cross-module
reference indexes have no rebuild path, and *"the CLI does not clear"* the same-module ones so a replay
leaves stale entries behind. **Every one of these backs a decision, not a screen.**

The domain-level fix is not a rebuild tool. It is that four of these five facts are *derivable* from live
aggregate state, and the model chose to cache them without a reconciler.

---

## DF-6 🟠 — `CollectionId` on descendants is derived data stored as fact, with the staleness in the event stream

*Already stated in `domain-model.md`; recorded because it is the cleanest instance of the pattern and its
severity is understated where it sits.*

> A cross-collection folder move raises `FolderMoved` for the moved folder only, so **descendant `Folder`
> and `MediaItem` aggregates keep the old `CollectionId` permanently** — a projection rebuild reproduces it
> rather than repairing it.

`folder.write-model.md` states the derivation in the same breath — *"a folder lives in whatever collection
its parent lives in"* — which is the tell. The observable outcome is that `FolderHierarchyIndex`, keyed on
`CollectionId`, puts **one subtree in two collections at once**.

Three options exist and the spec picks none: don't store it (resolve through the parent chain), emit
re-parent events across the subtree, or forbid cross-collection moves. Note that `Folder.CollectionId` is
already documented as **immutable** (`domain-model.md` § Folder: *"folders cannot move between
collections"*) while `MediaItem`'s assignment lifecycle says *"cross-collection permitted"* — so the third
option may already be half-taken and half-contradicted.

---

## DF-7 🟠 — The archive cascade is one operation with two opposite consistency contracts

*Tracked as MM-025/MM-026, X-11.17 still open. Included because the residual is a modelling question, not
a bug.*

`archive-fan-out.md` names it itself: *"⚠ **Neither invocation model is wrong on its own; having both
is.**"* Parent-before-children on Collection, parent-after-children on Folder; guarded on Folder,
unguarded on Collection; recoverable on Folder, and on Collection *"There is no way to re-trigger the
cascade through the API."*

The structural cause is ordering: `CollectionArchived` is published **first**, so the cascade is a
consumer of a fait accompli and has no channel to refuse. The spec's own proposal — *"making the
collection archive a *request* the cascade can refuse"* — is the right shape and is still marked **Open**.
Until then `Archived` means two different things in one bounded context depending on which aggregate you
read, and the operator note has to say so out loud.

---

## DF-8 🟠 — A metadata write can drive `Draft → Published`, from three handlers, bypassing `ReviewPolicy`

> Auto-submit fires from **three** handlers, not one … **A metadata write can take an item `Draft →
> Published`.** — `mediaitem.write-model.md`

Three problems stack:

- The completeness decision lives in three handlers rather than on the aggregate — the drift shape
  `folder.write-model.md` warns about directly (*"A guard in both places is a guard that will drift"*).
- Per D-7 the publish path *"never reads the profile's `ReviewPolicy`"*, so `AutoSubmitOnComplete` on a
  `RequiredForPublish` profile publishes with zero reviewers, silently.
- The dispatch is event-driven and at-least-once with no dedup key; a redelivery is refused
  indistinguishably from a real error.

This is the same class as DF-3: a policy field exists on the profile, is pinned into immutable versions,
and gates nothing. `mediaprofile.write-model.md` counts the scale — *"Two capabilities gate behaviour.
Seven gate nothing."*

---

## DF-9 🟠 — The behaviour gate reads the compiled RecordType union, not the declared capability set

> **a profile pinning no RecordType publishes an empty capability set** and gets no processing whatever it
> declared — `mediaprofile.write-model.md` § Which capability set reaches a MediaItem

`ToSnapshot()` copies the union of pinned RecordTypes' capabilities into `MediaItemCreated`, while
`MediaProfile.Capabilities` — what the author actually declared — *"goes to
`MediaProfilePublishedIntegrationEvent` and stops there."* A descriptive schema reference is being used as
a behaviour declaration.

The spec diagnoses this (U-6) and correctly rejects the tempting wrong fix. **What the fix note does not
say is that the wrong value is embedded in a persisted domain event**, so correcting the code repairs no
existing item — every one needs a replay or backfill, and `MediaItem.SnapshotFields` is documented
*"Immutable after creation"*.

---

## DF-10 🟠 — `ProcessingJob` mirrors the `Asset` lifecycle and is authoritative for none of it

`ProcessingJob` *"does **not** own the resulting asset state"* yet holds `AssetId`, `StorageKey`,
`ContentType`, `Renditions`, `Metadata` and `FailureCategory` — every one of which also lives on `Asset`.
Its status machine is a subset-mirror of `AssetStatus`, kept in step by a six-hop relay (saga → job command
→ job domain event → SNS → SQS → AM handler → Asset command).

The two then diverge and cannot reconcile. `processingjob.write-model.md` flags the mislabelling — a
validation timeout fails the **asset** with `ValidationTimeout` and the **job** with `ProcessingTimeout` —
and `Asset.CompleteProcessing` recovers only from `LastFailureCategory = ProcessingTimeout`. A late success
therefore takes the job to `Succeeded` while the Asset **refuses** and stays `ProcessingFailed`
permanently, and the refusal is invisible because the consumer never inspects the `Result`.

**The question this raises is whether `ProcessingJob` is an aggregate at all.** The saga already knows the
branch (it decides it) and the Asset already knows the outcome. The one thing an aggregate would add here
is idempotency, and `processingjob.write-model.md` admits it does not have it — *"a duplicate SQS delivery
… produces a **second job for the same asset**"*, overwriting the one-row-per-asset index that is the only
`AssetId → JobId` resolver the saga and scanner have.

---

## DF-11 🟠 — `RecordValidationResult`'s idempotency guard is its own post-state

Invariant: *"Status must be `Validating`."* Transition: *"`Validating → (RecordValidationResult: Pass) →
Validating (status unchanged …)"*. A status guard whose success leaves the status unchanged does not guard
against redelivery — a redelivered scan result raises a second `AssetValidationPassed` and a second
integration event.

This matters more than one endpoint because AssetManagement and Processing both delegate idempotency to
status guards by policy — *"Duplicate delivery is tolerated by **status guards**, not by a dedup key"* —
so this is the one place the platform-wide pattern has no teeth.

---

## DF-12 🟡 — The signing design's mutual exclusion is set after the irreversible act, from a projection

*In `document-signing/` (MM-038), parked. Flagged because it is a design flaw, not an implementation gap —
it should be fixed before the module is built, not after.*

`LinkSigningSession` *"is dispatched on `SigningEnvelopeCreated` rather than on initiation"*, and the
guard reads `ActiveSigningSessionId` off the eventually-consistent **detail read model**. Two stacked
windows: nothing is set during the adapter round-trip, and after that the check is against a projection.
Two concurrent initiations both pass, and the runbook concedes the outcome is not compensable — *"an
envelope sent to real signers cannot be unsent."*

Same ordering fault as DF-7. Two more from the same file worth carrying into the build decision:

- **Cancel during `Initiated` strands a live envelope.** Cancel is valid in `Initiated` — precisely when
  the adapter is calling the provider. The session goes terminal, `RecordEnvelopeCreated` is refused,
  `SigningEnvelopeLookupProjector` never writes the row, and per the write model that row is the **only**
  way a webhook resolves a tenant. Every subsequent callback for a live envelope is unresolvable, and
  nothing voids it.
- **Success and all three failures compensate identically**, and `RecordSignedAsset` sets `SignedAssetId`
  on the session only. Nothing attaches the signed document to the `MediaItem`; if the owner's manual
  step 12 never happens, the signed artefact — the point of the feature — is an orphan `Asset`.

---

## DF-13 🟡 — Cross-context invariants enforced on both halves, with no compensation on either

Two instances of the same shape:

- **Asset attach.** *"Catalog's `AssignAssetToRoleHandler` states outright that assignment carries **no**
  status constraint"*, while `Asset.AttachToMediaItem` enforces an allow-list and returns `422` otherwise.
  Catalog commits the assignment; AssetManagement then rejects it; `MediaItem.Assets` points at an asset
  whose `MediaItemId` is still null. No compensation either direction.
- **Assign-time quota.** `ApplyAssetAssignmentHandler` runs after Catalog has committed. The spec notes
  a refusal *"would make `ApplyAssetAssignment` fail an assignment Catalog has already committed"* and
  specifies no compensating `UnassignAssetFromRole`.

The invariant belongs to whichever side owns the role slot. Split across an async boundary with no
compensation, it is enforced by neither.

---

## DF-14 🟡 — Version-level RecordType deprecation has no enforcement path anywhere

`recordtype.scenarios.md` RT-4: *"A `MediaProfile` pinned to exactly v4 can no longer re-publish until it
re-pins. Catalog's refusal carries `supersededBy`."*

Contradicted twice: `mediaprofile.write-model.md` — *"`IsDeprecatedAsync` takes no version argument …
a deprecated *version* of a live record type is not caught. The refusal is a bare `InvalidOperation` and
carries no `supersededBy` pointer"* — and `Metadata/context-overview.md`, where
`RecordTypeVersionDeprecated` is *"⚠ not shipped."*

The whole retire-a-bad-version story, which is the reason `DeprecateRecordTypeVersion` exists, has no
enforcement. A profile pinned to a retired version republishes cleanly and keeps stamping the bad schema
onto new items. This is the one place `cross-aggregate-invariants.md` rule 11's careful per-version-flag
settlement (2026-09-04) has no consumer to make it true.

---

## DF-15 🟡 — Field deprecation destabilises metadata keys on items already created

`recordtype.write-model.md` exports a precedence contract Catalog is said to rely on. `mediaprofile.write-model.md`:

> `CompileTemplateAsync` filters on `!f.IsDeprecated` before collecting candidates, so a deprecated field
> is neither emitted nor counted toward collisions. **Neither `CompiledMetadataField` nor
> `MediaProfileSnapshotField` carries an `IsDeprecated` member.**

Because deprecated fields are not counted toward collisions, deprecating one contributor's colliding field
flips the *other* contributor's field from `{alias}.{fieldName}` back to a bare key at the next profile
publish. `MediaItem.SnapshotFields` is immutable after creation, so items created before and after the
deprecation store the same logical field under two different keys, and neither can be re-keyed.

Labelled an open question (U-3). It is larger than that: it is silent data loss on read, not a
documentation gap.

---

## DF-16 🟡 — Published contracts with no subscriber, and one consumer whose producer does not exist

| Contract | Evidence |
|---|---|
| `media.registration.submitted` / `.resubmitted` / `.confirmed` | *"⚠ Three of the six have no consumer"* — and confirmed is *"the primary cross-module signal"* (DF-1) |
| `media.item.deleted` | *"Published with no subscriber"* |
| 4 of 5 Collection events; **all** Folder events | *"Only `media.collection.archived` has a subscriber"*; *"No Folder integration event currently has a subscriber"* |
| `AssetDetachedFromMediaItem`, `AssetUnassignedFromRole`, `AssetReplacedInRole` | no mapper, no integration event — the search index learns of attachments and never of detachments |
| `RecordTypeVersionDeprecatedIntegrationEvent` | consumer specified, producer *"⚠ not shipped"* (DF-14) |
| All 9 signing domain events + their projector | *"orphaned (nothing emits them)"*; projector *"registered by no host"* |

Two things make this worse than dead code. **Registration's entire System half has no inbound trigger** —
`RecordSubmission`, `Confirm`, `Reject`, `ApproveAmendment`, `RejectAmendment` are all driven by an adapter
with no defined subscription (*"Step 5 happens because the adapter is watching"*), and the amendment
workflow is unreachable by design because the authority is never told an amendment was requested. And the
allowlist that routes any of it is *"a hand-maintained mirror of `ConsumerRegistrations` with nothing
enforcing the match"* (X-4.15) — adding a handler without its `[MessageType]` silently never delivers.

---

## DF-17 🟡 — Terminal states that still accept mutating commands

Three, in three contexts:

- **`MediaItem`.** `Archived` is *"Terminal soft-archive"*, yet move is legal on it — and
  *"`ArchiveMediaItemHandler` releases the title reservation on archive, so a subsequent move calls
  `MoveAsync` against a reservation row that no longer exists."*
- **`ChangeRequest`.** *"⚠ **`EditComment` and `DeleteComment` do not check `IsOpen`.**"* The discussion
  record behind a landed change stays editable, and `ReviewCommentEdited` deliberately carries no
  `OldBody`, so no evidence of the change survives.
- **`Registration`.** `Confirmed` is *"a permanent legal record"* whose only permitted change is
  *adding* a document via amendment. There is no route to correct a mistyped `Reference`, detach a
  document attached in error, or record that the authority revoked the filing. Meanwhile nothing stops the
  attached supporting `MediaItem`s from being withdrawn, archived or deleted afterwards (DF-2).

---

## DF-18 🟡 — `Folder.Close` carries retention semantics and cannot be reached

`folder.write-model.md`: *"nothing else in the aggregate guards on `IsClosed` — a closed folder can still
be renamed, moved, described and metadata-edited"*, and the enforcement that would matter — refusing
assignment into a closed folder — is *"⚠ **Specified, not implemented.**"*

`ClosedDate` is named as the clock source for a `Closure` retention trigger (DF-4), and D-11 records that
`POST /close` is a request-less endpoint, so the only settable path is at folder creation — the one moment
a folder is definitionally not closed. The field that carries the retention semantics cannot be populated.

---

## Two things that are not domain issues but change how all of the above behaves

**The platform contract and the app disagree about the outbox.** `aspnetcore-platform/CLAUDE.md` states as
a design constraint: *"Never publish integration events directly — always use `IOutbox` to ensure
atomicity with the write operation."* `consistency-model.md` records what magiq-media does: publication is
inline, after commit, with no outbox, and *"if the publish then fails, the event is committed and never
reaches a projector … the read model is wrong **permanently**."* Every reference index, counter and gate
in this review sits downstream of that. Tracked as X-11.44 / MM-035 and decision-gated; noted here only
because it converts several "eventually consistent" findings above into "silently divergent".

**Projections are synchronous in dev/qa/staging and asynchronous only in prod.** Per
`consistency-model.md` § Environment divergence, read-your-own-writes *"holds, accidentally"* everywhere
except production. Every ordering and staleness finding above is therefore unreproducible outside prod,
including DF-1, DF-3, DF-5 and DF-12.

---

## Recommended sequencing

1. **DF-1 and DF-2 together** — one decision (what `active-registrations` means) and one handler each.
   Smallest, and both are correctness-of-the-happy-path in a compliance context.
2. **DF-3** — decide whether the checkout gate is a real invariant. If yes it needs re-checking at submit
   and a binding between request, item and kind; if no, delete the policy rather than shipping a gate that
   fails open.
3. **DF-4** — settle before `RetentionSchedule` is built, not after. The migration is the hard part and it
   is unwritten.
4. **DF-8, DF-9, DF-14, DF-15** — one workstream. All four are the pinned-vocabulary seam
   `metadata-schema-composition.md` § Consequences already names as where the defects live: *"Four
   representations of a field definition between authoring and use."* Fixing them one at a time will not
   converge.
5. **DF-5, DF-6** — the derived-state family. Start at divergence *detection*, per MM-032's own advice, not
   at a rebuild tool.
6. **DF-10, DF-12** — both are "is this the right aggregate", answerable on paper before any code.

**Not recommended as work here:** DF-7, DF-11, DF-13, DF-16, DF-17, DF-18 are real but already have homes
(MM-025, MM-030, MM-038, the drift review). They are recorded so the flow argument is complete.
