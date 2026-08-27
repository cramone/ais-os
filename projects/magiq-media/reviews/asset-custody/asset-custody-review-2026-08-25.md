# Asset Custody — review

_Opened 2026-08-25. **Parked deliberately** — raised while classifying `Asset` for the ownership ADR during
W22 follow-up, and split out so the spec-drift work could continue. Nothing here is started._

---

## Why this is its own workstream

`Asset` was the last aggregate to classify in
[`docs/adrs/ownership-and-authorization.md`](../../../../D:/source/github/magiq-media/docs/adrs/ownership-and-authorization.md)
*(repo path: `docs/adrs/ownership-and-authorization.md`)*. The other six resolved cleanly — four provenance,
two standing. `Asset` did not, because it turned out to need **a third concept the codebase does not have**,
and describing that concept exposed **a live gap in the asset lifecycle**.

It is out of scope for the spec-drift review for a simple reason: **that plan corrects documentation against
code. This one changes code.**

---

## The model — decided, not built

An asset is the only aggregate here that can exist attached to nothing. Something must still be responsible
for it.

1. Uploaded → standalone, `MediaItemId` null. Someone is responsible until it is used.
2. Assigned to a `MediaItem` role → **the item's lifecycle governs; custody is dormant.**
3. Removed from that role → standalone again, and **whoever removed it decides its fate**: reuse, reassign,
   or destroy.

**Custody is what step 3 needs, and it transfers** — which is what separates it from the two concepts the
ADR already defines:

| | Changes hands? | Attached to |
|---|---|---|
| Provenance (`CreatedBy`) | Never | the resource |
| Authorization | n/a — a property of the actor | the actor |
| **Custody (`CustodianId`)** | **Yes, on detach** | the resource |

**Decision (ADR):** split `Asset.OwnerId` into `UploadedBy` (provenance, immutable) and `CustodianId`
(transfers to the detaching actor).

> The conflation is already in the declaration: `public UploaderId OwnerId { get; private set; }` — the type
> says uploader, the name says owner, one field does both jobs. It is assigned in the two creation `Apply`
> methods and **never changes**. No transfer event, no reassign method.

---

## The blocker — X-11.32

**Custody cannot transfer on detach, because detach never reaches the Asset aggregate.**

| Piece | State |
|---|---|
| `Asset.DetachFromMediaItem` | **Exists and is correct** — `Apply` clears `MediaItemId`, `RoleName`, `IsPrimary` |
| `DetachAssetFromMediaItemCommand` | **Dead** — appears once outside its own folder: its DI registration |
| Unassign consumer in AssetManagement | **Does not exist** — `AssetAssignedToRoleEventHandler` handles attach, no counterpart |
| `ApplyAssetAssignmentCommand` | **Attach only** — `MediaItemId` is non-nullable |
| Catalog's `AssetUnassignedFromRole` | Emitted; **consumed by nobody** in AssetManagement |

**Consequences, all live today:**

- After the first assignment, `MediaItemId` and `RoleName` are set permanently and `IsAssigned()` stays true.
- **The standalone state in step 3 is unreachable.**
- **An asset can never be reassigned to a different MediaItem** — attach requires a standalone asset.
- Custody has no transfer point to hang on.
- Backwards control: `AssetOwnership.CheckOwner` guards 8 commands including delete, so **the person who
  detaches an asset cannot decide its fate** — only the original uploader or a System actor can.

---

## Sequencing — this is the part that matters

**Three things, and the order is not negotiable:**

```
1. Wire the detach path          (X-11.32)   ← the lifecycle gap; nothing else is possible first
2. Model custody on top          (the ADR)   ← needs a transfer point to exist
3. Authorization replaces the interim owner checks
```

`AssetOwnership.CheckOwner` **must not be removed** before step 3. It is currently the only guard on 8
commands, and deleting it would widen **X-11.30** rather than clean anything up.

### Design constraint to settle first

The Asset-side handler runs in the **`EventConsumers`** host, which has **no HTTP actor**. So **the
detaching user's identity must travel on the integration event**, or the consumer has nobody to transfer
custody to. **Decide this when shaping the event, not afterwards** — it is the one choice that is expensive
to change later.

### Open questions for whoever picks this up

| # | Question |
|---|---|
| 1 | Who holds custody of an asset that is *never* assigned — the uploader indefinitely, or does it expire? |
| 2 | On detach, does custody go to the detaching actor, or back to the uploader? *(The stated intent is the detaching actor.)* |
| 3 | What happens to custody when an asset is promoted to `VersionArtifact` and later released? `VersionArtifactHolders` is a separate hold mechanism and may already answer this |
| 4 | Does detach need its own command and endpoint, or is consuming `AssetUnassignedFromRole` sufficient? The dead `DetachAssetFromMediaItemCommand` suggests the first was once intended |
| 5 | Should `MediaItemId` becoming null on detach be surfaced on the read model, so a client can list "my unassigned assets"? That is the screen the whole model implies and it does not exist |

---

## What was done, and what was deliberately not done

**Done:**

- The decision is recorded in `docs/adrs/ownership-and-authorization.md` — the custody concept, the split,
  the sequencing, and the design constraint.
- **X-11.32** (High — detach unwired) and **X-11.33** (the `Asset.cs:73` comment claiming `MediaItemId` is
  immutable once set, which `Apply` contradicts) are filed in
  `plans/spec-drift-review/spec-repo-drift-review.md`.

**Deliberately not done:**

- **No spec file was renamed.** The spec describes what the code does today; the ADR holds the decision.
  Renaming `OwnerId` in the spec ahead of the code would make the spec wrong in a new way and would need
  doing twice. This applies equally to the four provenance aggregates — `Collection`, `Folder`, `MediaItem`,
  `MediaProfile` — whose rename to `CreatedBy` is decided but unbuilt.
- **No plan folder was created.** Per `CLAUDE.md § Review → Plan`, a plan comes when the work is sequenced.
  This review is the argument; the plan is the checklist. Create `plans/asset-custody/` at that point, with
  the same folder name.

---

## Related

- `docs/adrs/ownership-and-authorization.md` (magiq-media repo) — the decision
- `plans/spec-drift-review/spec-repo-drift-review.md` — X-11.32, X-11.33, and X-11.30 for the
  authorization context
- `docs/spec/shared/authorization-matrix.md` (magiq-media repo) — what the 8 `AssetOwnership` guards
  actually cover
