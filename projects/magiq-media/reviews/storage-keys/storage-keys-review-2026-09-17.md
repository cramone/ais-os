---
id: MM-004
type: review
project: magiq-media
workstream: storage-keys
raised-by: [MM-003]
status: draft
outcome: pending
todo-id: 18a58118-5e58-5288-b177-36e0ec67a4fa
created: 2026-09-17
---

# Storage keys — one field, three definitions, and an object that moves

## Scope

**Read:** every statement about `StorageKey` in `docs/spec/` — the `Asset` write model, read model and
context overview, `ProcessingJob`, the `MediaItem` version-artifact snapshot, the shared storage and
messaging document, and the two architecture inventories.

**Not read:** any code. Nothing here is verified against `src/`, and the first sequencing step for
anything this review produces is to confirm which definition the implementation follows — see Q1.

**Raised by MM-003**, the spec-baseline remediation, while specifying the quarantine path. That work
needed to say where a quarantined object lives, discovered that the field which is supposed to answer that
disagrees with itself, and stopped rather than picking a side inside a plan that does not own the question.

---

## Why this is a review and not an MM-003 checklist item

MM-003's standing rule 4: *a new defect never becomes a checklist item here.* Nothing in MM-001 covers
this. SB-25 is about `AssetId` generation, not `StorageKey`; SB-19 settled where an infected object goes,
not how anything finds it afterwards. **Chase routed it here on 2026-09-17.**

The one thing MM-003 did commit to is narrow and holds either way: the quarantine retrieval route derives
its key rather than reading the stored one, which is correct under every option below.

---

## Findings

Severity is `Critical | High | Medium | Low`.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SK-1 | High | **`StorageKey` is specified three ways.** The write model and the domain-model inventory call it a **bucket + key pair**; the read model calls it **key path only, no bucket prefix**; the generator that produces it is documented as **single-bucket**. A consumer cannot tell from the spec whether the value it holds names a bucket. | `asset.write-model.md:149`, `domain-model.md:360` vs `asset.read-model.md:50`, `:223` vs `asset.write-model.md:174`, `:321` |
| SK-2 | Medium | **The same file disagrees with itself across two events.** `AssetUploadConfirmed` documents `StorageKey` as *"S3 key path"*; `AssetValidationPassed`, sixteen lines later, documents it as *"bucket + key — avoids a secondary lookup by the Processing Worker"*. Both are consumed by the Processing context. | `AssetManagement/context-overview.md:162` vs `:184` |
| SK-3 | Medium | **The read model already models bucket and key as two fields**, carrying `BucketName` beside `StorageKey`. That is the shape the rest of the spec does not use, and it is evidence that the key-only reading is the one in practice. | `asset.read-model.md:50–51`, `:223–224` |
| SK-4 | High | **After a quarantine move the stored value names the wrong bucket.** `StorageKey` is stamped once at upload and never re-derived, so a `ContainsVirus` asset's stored key still names `media-originals` while the object is in `media-quarantine`. The spec states this as deliberate and instructs readers not to use the field — a field that must not be read for the thing it names is a trap, not a design. | `event-store-and-messaging.md:493`; `asset.scenarios.md` § The quarantine move |
| SK-5 | Medium | **The value is denormalised into at least five places**, so any scheme that makes it mutable makes every copy stale rather than one: `ProcessingJob.StorageKey`, the asset detail and summary read models, `AssetUploadConfirmedIntegrationEvent`, `AssetValidationPassed`, and `ApprovedAssetSnapshot.SourceStorageKey`. | `processingjob.write-model.md:64`, `asset.read-model.md:50`, `context-overview.md:162`, `:184`, `mediaitem.write-model.md:488` |
| SK-6 | Low | **A known aliasing hazard already sits on the same field.** Two published versions can hold snapshot rows carrying the same `SourceStorageKey`, so a delete against one asset destroys an object the other version still points at. Recorded in the write model as a caution rather than resolved. | `asset.write-model.md:222–225` |

---

## The shape of the answer, as this review sees it

**Not a recommendation to adopt yet — Q2 decides it.** Stated so the questions have something concrete
to argue against.

**Derive the bucket; store only the key.** The key path is identical in both buckets that can hold an
original — `{tenantId}/{shard}/{assetId}/original.{ext}` — so only the bucket ever varies, and the bucket
is a function of what is being fetched:

| Fetching | Bucket |
|---|---|
| original, status ≠ `ContainsVirus` | `media-originals` |
| original, status = `ContainsVirus` | `media-quarantine` |
| rendition | `media-renditions` |

**What that buys.** SK-4 cannot occur, because the field never claimed to know the bucket. The structural
invariant *`StorageKey` is immutable after `AssetUploadInitiated`* survives intact — the key genuinely is
immutable, and only the bucket was ever changing. No new event, no migration, no mutable aggregate field.
It also picks the definition the read model and the generator already use, so it is less a change than a
decision to stop contradicting them.

**The alternative — update `StorageKey` on the move — is worse, and not for the obvious reason.** It
breaks the immutability invariant and it needs a domain event, which contradicts the standing statement
that quarantining is an infrastructure action with no domain visibility. But SK-5 is what decides it:
making the field mutable makes five stored copies stale instead of one.

---

## Open Questions

**Answered 2026-09-18 (Chase): correct the spec first, without reference to code.** That inverted the
sequencing this section assumed — Q1 was written as the first step and is now the last.

1. **Which definition does the code actually follow?** — **Deferred, deliberately.** Under the spec-wins
   rule adopted 2026-09-18, the code following a different definition is a **code defect**, not an argument
   about which document is right. So it stops being the gating question and becomes a verification item.
   **Routed to MM-002** with the other six from MM-006.

2. **Derive the bucket, or store it?** — **Answered: derive.** The shape above, adopted. Two things in the
   tree decided it rather than the argument: the read model already carries `BucketName` as a **separate
   field** beside `StorageKey`, and `AssetUploadConfirmed` carries both as separate members of a persisted
   event. A value already modelled alongside its bucket is not a bucket-and-key pair. SK-5 confirms it —
   storing the location makes the field mutable and leaves five stale copies instead of one.

3. **Is quarantine the only thing that moves an object between buckets?** — **Answered: yes.** The tier
   progression is an object *tag*, not a bucket change, and renditions are written once in place and now
   stop at Glacier Instant Retrieval without moving. Nothing else in the spec moves an object.

4. **Does `BucketName` on the read model stay?** — **Answered: it stays, restated as a record rather than
   an input.** Historically true on the event, currently true on the read model because the projector
   re-derives it when status changes, and consulted by nobody to locate an object. **No client-visible
   contract change and no event-shape change**, which is what made this the cheap answer.

5. **Is SK-6 in scope here?** — **Answered: no. It belongs to MM-002.** The spec records the aliasing
   hazard correctly; what destroys the object is code.

**Effect: SK-1 through SK-5 are closed by spec correction** (commit `8c661392`) — one definition, stated
in the file that owns storage, with the derivation table beside it. **SK-6 moves to MM-002.** What remains
here is Q1 as a verification item, which is no longer this review's to hold.

---

## Dependencies

**MM-003** — no blocking relationship in either direction. MM-003's quarantine text is consistent with
every option above, and this review changes nothing MM-003 has committed. If Q2 lands on *derive*, MM-003's
phase 8 fenced-content sweep is a convenient place to pick up any diagram that names a bucket.

**MM-002** — potential home for SK-6, and for whatever Q1 finds if the code and the spec disagree.

---

## Recommended sequencing

1. **Answer Q1 by reading `StorageKeyGenerator` and `StorageKey`.** One file, and it collapses SK-1, SK-2
   and SK-3 into either *the spec is wrong* or *the code is wrong*, which are different plans.
2. **Then Q3, then Q2.** Whether to derive depends on whether anything else will ever move an object, and
   answering them in the other order invites a decision that the next bucket overturns.
3. **Q4 last.** It is a contract change and only arises if Q2 lands on derive.

**No plan until Q1 is answered.** A plan written now would sequence edits to documents that may already be
describing the code correctly.
