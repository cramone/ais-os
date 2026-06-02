# ADR-010: MediaProfile Publish Guard Relaxation and MediaItem Conformance Tracking

**Status:** Accepted  
**Date:** 2026-05-21  
**Deciders:** Chase Ramone

---

## Context

Two related design questions arose during API layer implementation of `MediaProfile` and `MediaItem`.

### Question 1 — Publish guard strictness

The original publish guard required a draft to have ≥1 `AssetDefinition` **and** ≥1 `RecordTypeRef` before `PublishMediaProfile` could succeed. The intent was to prevent publishing a structurally empty profile. However, a `MediaProfile` has a third meaningful content class: `Capabilities`.

A capabilities-only profile (e.g. `Processing`, `VersionControl`) activates domain module behaviour on conforming `MediaItem`s without constraining asset slots or metadata schemas. This is a legitimate use case — clients may want to publish a minimal profile early to unblock dependent work, then add structural constraints via revision. The original guard blocked this entirely.

### Question 2 — Conformance drift after a profile revision

When a published profile is revised and republished with new required `AssetDefinition`s or required metadata fields (via `RecordTypeRef`), existing `MediaItem`s created against earlier versions of that profile may no longer satisfy the new requirements. Three options were considered for handling this:

**Option A: Block publish if existing items would be non-conformant**  
Prevents drift at source. Breaks the publish flow for profile owners who have no control over item content; too disruptive for large tenants.

**Option B: Block affected items from further operations until remediated**  
Strong enforcement, but creates operational lockout — items that were working before a profile revision become inoperable. Not appropriate for an async, eventually-consistent system where item owners may not be reachable immediately.

**Option C: Flag items as `PendingConformance`, allow remediation over time**  
Items remain readable and operable. A `conformanceStatus` field surfaces gaps clearly. Gaps self-resolve as required assets are assigned and required metadata fields are set. Profile owners can publish revisions freely; item owners are notified of what needs to be filled in.

---

## Decisions

### Decision 1 — Relax the publish guard

**Chosen:** Publish is valid if the draft has ≥1 `Capability`, ≥1 `AssetDefinition`, or ≥1 `RecordTypeRef`. An entirely empty draft (no content of any kind) remains blocked with `MediaProfileEmpty`.

**Rationale:** Capabilities are first-class content on a `MediaProfile`. A profile that activates `Processing` or `VersionControl` is not empty — it has a defined contract, just not a structural one. The original guard was overly strict and prevented incremental rollout patterns.

The relaxed invariant in `MediaProfile.Publish()`:

```csharp
var hasContent = Draft!.AssetDefinitions.Any()
    || Draft.RecordTypeRefs.Count > 0
    || Draft.Capabilities.Any();

if (!hasContent)
    return DomainError.InvalidOperation(
        "Cannot publish a profile with no capabilities, asset definitions, or record types.");
```

### Decision 2 — Conformance tracking: flag, do not block

**Chosen:** Option C — `MediaItem` gains a `ConformanceStatus` (`Conformant` | `PendingConformance`) and a `ConformanceGaps` list. Items are never blocked by a profile revision.

**Rationale:** Blocking would impose synchronous remediation requirements on item owners at the moment a profile owner publishes a revision. These are decoupled actors. Flagging gives clients the information they need to surface gaps in the UI and prompt users to remediate, without preventing reads, metadata updates, or other operations that do not depend on the missing requirements.

`ConformanceGap` carries enough information to action the remediation:

```csharp
public enum ConformanceGapType
{
    MissingRequiredAssetRole,
    MissingRequiredMetadataField
}

public sealed record ConformanceGap(ConformanceGapType GapType, string Identifier);
```

`Identifier` is the `RoleName` for `MissingRequiredAssetRole` and the field name for `MissingRequiredMetadataField`.

### Decision 3 — Gaps self-resolve; no explicit "mark conformant" API

**Chosen:** `ConformanceStatus` transitions from `PendingConformance` back to `Conformant` automatically when all gaps are satisfied. No `PATCH /conformance-status` endpoint is needed or provided.

**Rationale:** The state that drives conformance (`Assets` and `Metadata`) is already mutated through existing write paths (`AssignAssetToRole`, `SetMetadataField`, `SetMetadataBatch`). Re-evaluating gap resolution inside the aggregate's apply logic — via a `TryResolveConformanceGaps()` helper — means the transition is always consistent with actual item state, with no client coordination required.

The only gap in this approach is partial batch metadata sets: if a batch sets some but not all required fields, conformance is re-evaluated after each event, not after the full batch completes. This is acceptable — the intermediate state is still accurate.

### Decision 4 — Fan-out uses `media-item-profile-index`; scale limit at 1,000 items

**Chosen:** When `MediaProfilePublishedMessage` is received, the conformance fan-out handler iterates pinned `MediaItem`s via a paginated `media-item-profile-index` (PK: `TENANT#{TenantId}#PROFILE#{MediaProfileId}`). A warning is logged if the item count for a given profile exceeds 1,000. Batch re-evaluation for very large profiles is deferred to a future async job pattern.

**Rationale:** Inline fan-out is consistent with the existing `MediaProfilePublishedMessage` consumer pattern (which already fans out to update `media-item-capability-refs` and `media-item-registration-refs`). The 1,000-item threshold is a pragmatic limit for the current single-Lambda execution model. Profiles with very large item populations are expected to be system-level or platform-default profiles, which change infrequently. A dedicated reprocessing job can be added when that use case is confirmed.

The `media-item-profile-index` is a net-new DynamoDB projection table maintained by a projector reacting to `MediaItemCreated` and `MediaItemDeleted`/`MediaItemArchived`. Existing items require a projection replay to seed the index in non-empty environments.

---

## Consequences

**Positive:**
- Capabilities-only profiles are first-class. API clients can publish a minimal profile immediately and iterate structure via revisions — consistent with how `RecordType` and other schema-driven aggregates work.
- Item owners are never blocked by a profile owner's revision. The system remains operable across a revision window.
- Gap list is actionable — role name and field name are surfaced directly; no client-side inference needed.
- Auto-resolution means the UI can drive users through a checklist without requiring a separate API call to confirm completion.

**Negative / Trade-offs:**
- `media-item-profile-index` is a new index table. Projection replay required on existing non-empty environments before the fan-out handler can be deployed.
- `TryResolveConformanceGaps()` is called on every `AssetAssignedToRole`, `MetadataFieldSet`, and `MetadataBatchSet` apply path, even for `Conformant` items. The guard `if (ConformanceStatus == Conformant) return;` makes this O(1) for the common case.
- The 1,000-item fan-out limit means very large profiles (platform defaults, system profiles) may require a separate re-evaluation job after a revision publish. This is a known deferred item.
- `ConformanceStatus` is not surfaced on the write-side aggregate's integration events (`MediaItemCreatedIntegrationEvent`, etc.). Downstream contexts do not need it; it is a Catalog read-model concern only.

---

## Related

- [MediaProfile Write Model](../spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md)
- [MediaItem Write Model](../spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md)
- [ADR-005 — Integration Event Publisher](./ADR-005-integration-event-publisher.md)
- [media-profile-conformance-plan.md](../../../repos/magiq-media/media-profile-conformance-plan.md) — full implementation plan
