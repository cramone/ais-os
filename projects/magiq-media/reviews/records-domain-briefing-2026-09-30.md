# Records-domain briefing — Karen session 2026-09-30

Eleven records-policy decisions pending. Eight from spec-audit-2026-09-29 open with `decision-owner: records-domain`; three from spec-audit-2026-09-28 Wave 4 blocked on the same calls. Each item below: **today**, **options**, **spec files touched**. All items decided here are stated in `docs/spec/` or `docs/adrs/`; none involves code at this phase.

---

## From spec-audit-2026-09-29 (eight open, decision-owner: records-domain)

### F004 — Archived item under live registration: delete behaviour + race recovery

**Today.** `AddRegistrationRef` has no status guard and `DeleteMediaItem` does not consult `RegistrationIds`. A concurrent initiate+archive (within replica lag) leaves an archived item under a live statutory filing; the item can then be destroyed while the registration is `Confirmed`. No detector exists.

**Options.**
- **A — Guard delete + detect race.** Add `RegistrationIds` empty → `MediaItemHasActiveRegistrations` to `Delete`. `AddRegistrationRef` on an archived item raises `RegistrationRefAddedWhileArchived`, operator alert, state recovery (un-archive via cascade root, or record registration against archived record). *Consequence:* destruction of a filed record becomes impossible without first withdrawing the filing; race leaves a flagged but preserved record.
- **B — Status quo + document the hole.** Add `§ Not supported` entry stating the race is accepted and the registration survives on an archived/destroyed subject. *Consequence:* loses evidence; indefensible at audit for a records platform.

**Spec files.** `docs/spec/shared/cross-aggregate-rules.md` (rule 13 restatement) · `docs/spec/shared/cascade-rules.md` § Hard delete · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` (`Delete` guard, `AddRegistrationRef`, invariants table, new domain event).

---

### F036 — Infected original on reprocess attempt ≥2 of a version-held asset

**Today.** `RequestReprocessing` has no version-hold check. A rescan of a published record's asset can return `VirusDetected`; the quarantine path deletes the original after 90 days with no `RetentionSchedule`, hold or disposal authority consulted — contradicts ADR premise that holders cannot destroy a referenced record.

**Options.**
- **A — Retain under holders.** Quarantine 90-day expiry applies only to attempt-1 assets never version-held. Any version-held or ever-`Active` asset is retained while any holder is under retention or legal hold; disposed only through the holder's disposition. *Consequence:* potentially-malicious originals persist in the quarantine bucket for years; serving path already excludes them.
- **B — Refuse the rescan.** `RequestReprocessing` refuses on version-held assets (`AssetIsVersionHeld`). *Consequence:* no new attempt means no new infection record; signature-update catches on records are impossible until the version is purged.

Attempt ≥2 renditions on infection: moved with original or deleted on `AssetInfectionDetected` — decide alongside.

**Spec files.** `docs/spec/shared/event-store-and-messaging.md` § Quarantine bucket (retention rule) · `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md` (reprocess guard or rendition-on-infection rule) · `docs/adrs/infected-originals.md` (decision record).

---

### F039 — Legal hold reach to detached assets

**Today.** Hold check on asset erasure reads the asset's `MediaItemId`, which `AssetDetachedFromMediaItem` clears. Two routes alter/destroy held-record content without touching the hold: (1) `EraseAssetPersonalData` shreds `OriginalFileName`/`ExifData` of an artifact of a version of a held record; (2) `UnassignAssetFromRole`/`ReplaceAssetInRole`/`DeleteAsset` destroy draft-attached assets on a held item.

**Options.**
- **A — Hold set = every item that holds the asset.** `(attached item ∪ VersionArtifactHolders)`. A hold on any member refuses erasure. Add `MediaItemUnderLegalHold` to `UnassignAssetFromRole`, `ReplaceAssetInRole`, `DeleteAsset`. *Consequence:* editing a held item's asset roster becomes impossible until hold lifts.
- **B — Propagated hold marker on asset.** `LegalHoldPlaced` fans out a marker to every asset in `VersionArtifactHolders`; marker maintained from Catalog events. `DeleteAsset`/`EraseAssetPersonalData` check the marker. *Consequence:* preserves asset-roster edits on held items (never-published drafts remain mutable); adds fan-out complexity and reconciliation burden.

**Spec files.** `docs/spec/shared/personal-data-and-erasure.md` § Precedence · `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md` § Invariants + § Erasure · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` § Legal holds + § Invariants · `docs/adrs/retention-and-disposal.md` · `docs/adrs/personal-data-and-erasure.md`.

---

### F059 — Registration supporting documents under live/confirmed filing

**Today.** `RegistrationItemAttached` and amendment events do not cross the module boundary, so attached-document items never populate `RegistrationRefs`. A supporting document can be archived + hard-deleted at any time, leaving `Confirmed` registration pointing at destroyed evidence. Spec is silent.

**Options.**
- **A — Protect documents.** Publish `media.registration.item-attached` (and amendment-approved attach). Catalog records reference in `RegistrationRefs` with role `Subject | Document`. Rule 13 and delete guard cover documents. Add row to cross-aggregate-rules.md. *Consequence:* document items inherit the same lifecycle rigidity as subject items.
- **B — State the exclusion.** Add to registration.write-model.md § Not supported: "No protection of attached documents. Legal hold is how a tenant preserves them." Record rationale in `registration-filings.md`. *Consequence:* evidence loss is tenant-admin responsibility; filings may dangle; defensible only if ADR's "evidence outlives the transferred thing" argument is scoped to the subject.

**Spec files.** `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md` · `docs/spec/shared/cross-aggregate-rules.md` (if A) · `docs/adrs/registration-filings.md` (rationale).

---

### F088 — Reopening a closed folder: retention clock on `Closure`-pinned items

**Today.** `RetentionStartedAt` is immutable except through re-closure. Reopen clears the closure but not the stamps; a reopened never-re-closed folder holds records with a disposal clock running from a closure that no longer exists. (Un-archive half already decided — stays running.)

**Options.**
- **A — Clear on reopen.** Reopen fans out `RetentionClockCleared` to every `Closure`-pinned item filed in it; re-close re-stamps as if first close. *Consequence:* mirrors the deliberate-act argument; needs fan-out mechanism + F042/F043 reconciliation.
- **B — Suspend on reopen.** Clock halts; a later re-close resumes from the suspended elapsed value. *Consequence:* same fan-out; semantics closer to litigation-hold.
- **C — Keep running (status quo made explicit).** State in retention-and-disposal.md: "Reopen does not alter the clock." *Consequence:* records disposed on clocks pinned to undone closures; indefensible at audit.

**Spec files.** `docs/adrs/retention-and-disposal.md` (decision) · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` § Retention · possibly `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md` § Reopen (fan-out trigger).

Fix with **F089**. Held by spec-audit-2026-09-28/shared-arch/F022.

---

### F089 — Archiving a never-closed folder

**Today.** Archive is the ordinary folder end-of-life; nothing requires prior closure. Once archived, close is refused — so every `Closure`-pinned item in it has a trigger that can never occur. Record sits with a schedule and no start, indistinguishable from one whose folder is still open.

**Options.**
- **A — Archive closes.** `ArchiveFolderNode` raises `FolderClosed` with `ClosedDate = archivedDate` before `FolderArchived`; closure fan-out runs as normal. *Consequence:* matches records practice (file closed before transferred to archive); no new refusal in cascade pre-flight.
- **B — Archive refuses.** Invariant: "Not open while any item filed in it holds a `Closure` pin" → `FolderNotClosed` on `ArchiveFolder` and each folder in a collection-cascade pre-flight. *Consequence:* forces explicit close; cascade pre-flight gets wider; existing archived-never-closed folders in deployed envs need remediation guidance.

**Spec files.** `docs/adrs/retention-and-disposal.md` (decision) · `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md` § Status transitions / § Invariants · `docs/spec/shared/cascade-rules.md` (if B).

Fix with **F088**. Held by spec-audit-2026-09-28/shared-arch/F022.

---

### F090 — Person-bearing free text on MediaItem/Folder/Collection/ChangeRequest

**Today.** Erasure table lists four scopes (Registration, Asset, ChangeRequest comment, DocumentSigningSession). `MediaItem.Author` (by definition a person), `Title`, `Description`, `General`-origin metadata values, `Folder.Originator`, `Collection.Description`, ChangeRequest `Title`/`Reason` all free text written by people — unclassified. Classification is at first-write; omission is permanent, not fixable later.

**Options.**
- **A — Erasure scope.** Add rows: MediaItem (`Author`, `Description`, `General`-origin values), Folder (`Originator`, `Description`), ChangeRequest extended to `Title`/`Reason`. New erase commands + events per aggregate. Governed metadata needs per-field `Personal` flag on `RecordType` field def pinned into snapshot, encrypted from first write. *Consequence:* privacy-complete; erases record content the regulator may require preserved.
- **B — Retained record content.** State each exclusion under § Structural values are not personal data ("A media item's `Title` is the record's name and is not personal data"). Record reasoning in ADR. *Consequence:* retention governs these; GDPR/privacy requests cannot touch record body — tenants must use retention disposal instead.
- **C — Split.** `Author` to erasure (no structural reading); `Title`/`Description`/`Originator` to retained content; governed metadata field-by-field via `Personal` flag.

**Spec files.** `docs/spec/shared/personal-data-and-erasure.md` (table + § Structural) · `docs/adrs/personal-data-and-erasure.md` (rationale) · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` (if A: erase command/event) · same for Folder, Collection, ChangeRequest write-models · `docs/spec/contexts/Metadata/aggregates/RecordType/*` (if `Personal` flag added).

---

### F091 — Hard delete tombstone: reason + disposal authority

**Today.** `MediaItemDeleted` carries `MediaItemId`, `FolderId?`, `MediaProfileId?`, `DeletedAt` — no reason, no authority. `PurgeMediaItemVersion` requires `Reason`; `DeleteAsset` accepts one. Nothing refuses deleting a record whose schedule says `RetainPermanently` or whose period has not elapsed. ADR audit question "which instrument authorised this" is unanswerable per deletion.

**Options.**
- **A — Record only.** Add required `Reason` to `DeleteMediaItemCommand`. `MediaItemDeleted` additively carries `Reason`, `RetentionScheduleId?`, `ScheduleVersion?`, `RetentionStartedAt?` as they stood at deletion. Absent-meanings stated for existing events. No refusal. *Consequence:* audit trail only; a tenant can still destroy a `RetainPermanently` record and leave a reason.
- **B — Record + refuse.** Same event additions. Delete refuses if pinned period not elapsed or `RetainPermanently` → `MediaItemRetentionActive` / `MediaItemRetainedPermanently`. *Consequence:* enforced disposal authority; needs an override path (break-glass with reason) or a retention-schedule-override command for defensible early disposal.
- **C — Record + refuse + override.** B plus an explicit `OverrideRetention` reason category that is recorded but admitted. *Consequence:* defensible for both honest and exceptional cases; most spec surface.

Note: `DELETE` request body has no defined semantics under RFC 9110 §9.3.5; if purge route uses a body, state both do; otherwise `Reason` goes on query string or move to `POST .../dispositions`.

**Spec files.** `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` § Domain Events + § Commands · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md` (DELETE route body/query) · `docs/adrs/retention-and-disposal.md` (A/B/C decision + scope expansion, since ADR currently excludes any `DeleteMediaItem` link).

---

## From spec-audit-2026-09-28 Wave 4 (three blocked)

### shared-arch/F022 — Retention trigger types + clock-start events enumeration

**Today.** Spec explains Closure trigger (folder closure stamps clock on filed items) but does not enumerate the full set of trigger types or what events qualify as clock-start events for each. Missing trigger means records never disposed or disposed without authority; neither detectable from spec. Blocks F088/F089.

**Options.**
- **A — Minimal enumeration (Closure + Archived only).** State in `retention-and-disposal.md`: "Supported triggers are `Closure` (stamped on filing folder closure) and `Archived` (stamped on `MediaItemArchived`)." Nothing else starts a clock. *Consequence:* simplest; matches current invariants; `DateReached`/`EventBased` deferred until requested.
- **B — Full enumeration with placeholders.** Enumerate `Closure`, `Archived`, `DateReached`, `EventBased`, `Permanent` (RetainPermanently sentinel). State each clock-start event (or "trigger not supported, no clock" for Permanent). *Consequence:* spec surface for triggers that have no handler; implementation gap vs record list; audit-complete.
- **C — Jurisdiction-driven list.** List triggers supported by AU PSPF + NZ PSR + GDPR + any US schedule. *Consequence:* needs Karen's authoritative list; delays close.

**Spec files.** `docs/adrs/retention-and-disposal.md` (enumeration + rationale) · `docs/spec/shared/personal-data-and-erasure.md` (trigger-list restatement if cross-ref) · `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.write-model.md` (trigger-type value object + validation) · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` § Retention (stamp sources).

---

### ctx-metadata/F006 — `RetentionScheduleDeprecated` cascade

**Today.** cascade-rules.md states existing pins unaffected on deprecation; nothing states (1) whether Catalog consumes `RetentionScheduleDeprecatedIntegrationEvent`, (2) whether the disposal clock continues on affected items. Items could be disposed under a superseded schedule, or held indefinitely with no resolution path.

**Options.**
- **A — Clock continues, items flagged.** Catalog handles `RetentionScheduleDeprecatedIntegrationEvent`; adds `RetentionScheduleDeprecated: true` flag to detail row of each item pinned on it. Clock continues (pin is a snapshot). Users notified to re-pin before disposal. *Consequence:* preserves immutability of pins; forces user re-pin; disposal under superseded schedule still legal until re-pin.
- **B — Clock continues, no handler.** State explicitly: "No Catalog-side handler. Deprecation is a policy signal; existing pins execute to disposal." *Consequence:* smallest spec; users have no visibility; relies entirely on administrator process.
- **C — Clock freezes, forced re-pin.** On deprecation, Catalog freezes clock on affected items and refuses disposal until repinned. New command `RepinRetentionSchedule`. *Consequence:* no silent disposal under superseded schedule; new refusal path; backlog of items awaiting re-pin.

**Spec files.** `docs/spec/shared/cascade-rules.md` § RetentionSchedule deprecated · `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.write-model.md` § Deprecate (restatement of downstream) · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` (if A: new flag; if C: freeze + repin command/event) · `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.read-model.md` (if A: flag in detail row) · `docs/adrs/retention-and-disposal.md` (rationale).

---

### ctx-registration/F005 — Crypto-shred key store concrete name

**Today.** Spec specifies crypto-shredding "rests on a platform key store and field-level encryption in the event serializer" but does not name: key store identity (KMS? platform DynamoDB table? HSM?), key lifecycle, retry mechanism for destruction, scope (does erasure cover in-flight SNS/SQS/outbox copies, or only event-store + snapshots?). Implementer cannot determine whether the erasure guarantee holds for messages in-flight at erasure time.

**Options.**
- **A — Name AWS KMS + state in-flight gap.** Key store is AWS KMS; key alias `media/erasure/{scope-type}/{scope-id}` or similar; retry is a scheduled scanner over `media-erasure-pending` until `ScheduleKeyDeletion` succeeds. State explicitly: "Erasure covers event-store payloads, snapshots and outbox envelopes. In-flight SNS/SQS messages are decrypted on receive and may remain readable in a DLQ for up to its retention (7–14 days)." *Consequence:* complete but admits a bounded exposure window; may need regulator-visible mitigation.
- **B — Name platform abstraction only.** State "managed by `Magiq.Platform.Encryption`; concrete store is a cross-cutting platform decision." Punt to platform spec. *Consequence:* records-domain unblocked; cross-cutting platform spec still owes the answer.
- **C — Cover in-flight.** Encrypt payload members under the scope key end-to-end: envelopes carry ciphertext, subscribers decrypt only inside the consumer with a KMS call. Key destruction invalidates every copy including DLQs. *Consequence:* strongest guarantee; new per-event KMS cost; subscriber complexity.

**Spec files.** `docs/spec/shared/personal-data-and-erasure.md` § The mechanism — crypto-shredding · `docs/adrs/personal-data-and-erasure.md` § Consequences · `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md` § Erasure of personal data (cite platform capability) · possibly new `docs/spec/shared/platform-encryption.md` or extension of `event-store-and-messaging.md` § Erasure (if C: envelope-ciphertext path).

---

## Dependency map

- **F088 ↔ F089 — decide together.** Both touch retention clock lifecycle; both held by shared-arch/F022.
- **shared-arch/F022** gates F088, F089, F091, ctx-metadata/F006. Enumerate triggers first.
- **F090 ↔ F039** — both classify what can be erased on a record; keep aligned.
- **F004 ↔ F059** — both decide on registration-side evidence preservation. Choose a single theory of "what survives on the subject vs document side".
- **F036 ↔ F039** — infection quarantine (F036) option A ("retain under holders") depends on F039 option A/B (define the hold set).
- **ctx-registration/F005** independent of records-policy choices; platform-engineering flavoured but needs Karen's sign-off on in-flight-exposure window.

## Suggested session order

1. F022 enumerate triggers (gate) → F088 + F089 together → F091
2. F039 hold set → F036 quarantine policy
3. F090 personal-data vs record-content classification
4. F004 archive race recovery → F059 attached-documents protection
5. ctx-metadata/F006 deprecation cascade
6. ctx-registration/F005 crypto-shred key store

## Decision tracker

- [x] shared-arch/F022 — retention trigger enumeration → **CLOSE, no spec edit** (current spec already enumerates Creation/Published/Archived/Closure with clock-start events in both ADR and `retentionschedule.write-model.md § Trigger vocabulary` + `mediaitem.write-model.md § Retention`; "ships whole" ADR position stands; finding was stale)
- [x] F088 — reopen clock behaviour → **A refined** (reopen fans out `ClearRetentionClock(expectedClosedAt)`; guard `RetentionClosureAt == expectedClosedAt`; raises `RetentionClockCleared`; re-close re-stamps via existing fan-out; immutability clause rewritten; ADR § A Re-Closure renamed to § A Reopen Clears, a Re-Closure Re-Stamps)
- [x] F089 — archive never-closed folder → **A refined** (archive closes: `ArchiveFolderNode` raises `FolderClosed(closedAt=archivedAt, closedDate=archivedDate)` if not already closed, then `FolderArchived`; closure fan-out runs; un-archive leaves closure in place → `Active + Closed`, separate `Reopen` restores accession; cascade walks subtree closing en route; no backfill — no production data)
- [x] F091 — delete tombstone reason + authority → **C refined** (single `DisposeMediaItemCommand(Reason, OverrideAuthority?)` replaces `DeleteMediaItemCommand`; `POST /v1/items/{itemId}/dispositions` replaces `DELETE /v1/items/{itemId}`; `MediaItemDeleted` extended with `Reason, RetentionScheduleId?, ScheduleVersion?, RetentionStartedAt?, OverrideAuthority?`; override detectable by `OverrideAuthority IS NOT NULL`; new refusals `MediaItemRetentionActive`, `MediaItemRetainedPermanently`; legal hold unconditional; ADR § Scope expanded to disposal act, engine stays out)
- [x] F039 — legal hold reach to detached assets → **A refined (split mechanism)** — (1) MediaItem self-refuses content-mutating commands when hold in force (`UnassignAssetFromRole`, `ReplaceAssetInRole`, `AssignAssetToRole`, `ReorderAssetsInRole` → `MediaItemUnderLegalHold`); (2) Asset carries `HoldersUnderHold: Set<MediaItemId>` replica maintained from new Catalog→Asset integration events `media.mediaitem.legal-hold-placed/lifted` carrying `AffectedAssetIds[]`; `DeleteAsset` + `EraseAssetPersonalData` on detached asset check the replica; reconciliation CLI `catalog rebuild-asset-holder-holds` provided
- [x] F036 — infected reprocess on version-held asset → **A refined** (predicate = `IsVersionHeld` at infection time; `QuarantineRetentionPolicy: FixedPeriod | UnderHolders` stamped on `AssetInfectionDetected`; `UnderHolders` skipped by expiry scanner, disposed via holder's F091-C disposition flow; attempt ≥2 renditions deleted on `AssetRenditionsDiscardedOnInfection`; `RequestReprocessing` stays admitted on version-held assets for signature-update rescans)
- [x] F090 — person-bearing free text classification → **C1 refined** (minimum split: MediaItem.Author as new 5th erasure scope via `EraseMediaItemPersonalData` + `MediaItemPersonalDataErased`; Title/Description/Folder.Originator/Folder.Description/Collection.Description/CR Title+Reason stated as retained record content; governed metadata via per-field `Personal` flag on `RecordTypeField` pinned into `MediaProfileSnapshotField`, encrypted under item's erasure key from first write)
- [x] F004 — archive race + delete guard on registrations → **A refined** (`DisposeMediaItem` guards `RegistrationIds` empty → `MediaItemHasActiveRegistrations`; `AddRegistrationRef` on archived item raises both `RegistrationRefAdded` + `RegistrationRefAddedWhileArchived`; publishes `media.mediaitem.registration-added-while-archived` for operator alert + audit; `Catalog.ArchivedItemsWithActiveRegistrations` metric; recovery via un-archive OR F091-C disposal override; override cannot cover active registrations — spoliation of filings not a retention exception; no new verb)
- [x] F059 — registration supporting documents protection → **A refined** (publish `media.registration.item-attached` + `media.registration.item-detached` for both direct + amendment-approved attach; Catalog records in `RegistrationRefs` with `Role: Subject | Document` + `ItemType?`; `RegistrationIds` covers both roles; rule 13 extended "subject OR attached document"; cascade-rules hard-delete updated; absent-meanings for stored events; role-based disposal enabled by discriminator but not required; pairs with F004 race-detector + F091-C disposal guard)
- [x] ctx-metadata/F006 — RetentionScheduleDeprecated cascade → **A refined + A2 re-pin** (new consumer `RetentionScheduleDeprecatedIntegrationEventHandler` fans out via Step Functions Distributed Map over new `MediaItemByRetentionScheduleIndex`; dispatches `RecordRetentionScheduleDeprecation` per item; item records `RetentionScheduleDeprecated`, `RetentionScheduleDeprecatedAt`, `SupersededByRetentionSchedule?` via new `RetentionScheduleDeprecationRecorded` event; detail row carries flags + list filter; clock continues on existing pins; **re-pin admitted only to named `SupersededBy` successor** when deprecation-flagged — narrow carve-out, deliberate+evented+authority-anchored; reconciliation CLI `catalog rebuild-retention-schedule-deprecations`; cascade-rules + ADR § Deprecation does not disturb the pin updated)
- [x] ctx-registration/F005 — crypto-shred key store concrete name → **A refined** (AWS KMS Customer-Managed Keys per erasure scope under alias `media/erasure/{scope-type}/{scope-id}` with 5 scope-types incl. new mediaitem from F090; envelope encryption via `GenerateDataKey`/`Decrypt`; destruction via `ScheduleKeyDeletion(PendingWindowInDays=7)`; retry via scanner on `media-erasure-pending` table; three-channel coverage statement — integration events identifier-only + intra-BC exception encrypted under owning scope + webhook DLQ identifier-only — closes any in-flight window; no 7-14 day exposure window conceded; metrics on `MediaErasurePending.*`; all five erasure scopes cite the platform mechanism)

---
*Prepared 2026-09-30 from docs/review/spec-audit-2026-09-28 and spec-audit-2026-09-29. No spec files edited.*
