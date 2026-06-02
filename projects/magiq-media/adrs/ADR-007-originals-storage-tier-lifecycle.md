# ADR-007: Originals Storage Tier Lifecycle Policy

**Status:** Accepted  
**Date:** 2026-05-14  
**Deciders:** Chase Ramone

---

## Context

The `media-source` bucket holds original uploaded assets. We need a cost-optimal storage tier progression that balances access latency, retrieval cost, and the reality that originals may still be accessed well beyond 90 days.

The initial implementation used a **tag-based** lifecycle rule: only S3 objects tagged `archived=true` (intended to be stamped by the Processing Worker on `AssetArchived`) would transition to Glacier Instant Retrieval after 90 days.

This approach had two problems:

1. **Tag-setting code was never implemented.** No application code called `PutObjectTagging`, making the lifecycle rule a dead letter.
2. **90 days to Glacier is too aggressive.** Active, non-archived assets may still be retrieved after 90 days (e.g., re-processing, compliance access, user download). Glacier Instant Retrieval carries a retrieval fee and a 90-day minimum storage commitment that creates cost inefficiency for objects deleted or transitioned within that window.

---

## Decision

Replace the tag-based single-transition rule with a **time-based, four-tier lifecycle** applied to **all objects** in `media-source`, keyed from the object creation date:

| Age from creation | S3 Storage Class |
|---|---|
| 0 – 90 days | Standard |
| 90 – 365 days | Standard-IA |
| 365 days – 2 years | Glacier Instant Retrieval |
| 2+ years | Deep Archive |

No tag filter. The policy applies unconditionally to every object in the bucket.

The `s3:PutObjectTagging` permission is removed from the Processing Worker IAM role — it is no longer needed.

---

## Consequences

**Positive**
- Originals are accessible without retrieval fees for the first year, which covers the vast majority of active access patterns.
- Cost decreases significantly for long-lived originals (Deep Archive is ~$1/TB/month vs. ~$23/TB for Standard).
- Eliminates a dead-code dependency (tag-setting was unimplemented and untested).
- Simpler CDK — no `tagFilters`, no application-layer S3 tagging obligation.

**Negative / Trade-offs**
- All objects transition regardless of `AssetStatus` (Active, Archived, Deleted). Objects in Deleted or Archived state will still cost Standard pricing for the first 90 days rather than moving immediately to a cheaper class. Accepted — the cost delta for the 0–90 day window is small and the simplicity benefit outweighs it.
- Objects deleted or transitioned to a lower class before the S3 minimum storage duration (30 days for Standard-IA, 90 days for Glacier Instant) incur a pro-rated minimum storage charge. This is a known S3 cost model characteristic, not a problem introduced by this ADR.
- Deep Archive has a 12-hour retrieval time. Objects older than 2 years that need urgent access require an explicit S3 Restore before they can be served. The application must handle the `InvalidObjectState` error from `GetObject` and surface this to callers. **This error path must be implemented before production.**

**Domain model changes**
- `StorageTier` enum gains `GlacierInstant` and `DeepArchive`. The existing `Glacier` value is retained as a legacy alias for event-store backward compatibility (old `AssetStorageTierTransitioned` events in DynamoDB used `Glacier`).
- `Asset.Archive()` no longer emits `AssetStorageTierTransitioned`. Tier transitions are now driven entirely by the bucket lifecycle and are recorded asynchronously by the `StorageTierTransitionScanner`.
- A new `RecordStorageTierTransitionCommand` (system actor only) is added to the write model. The `StorageTierTransitionScanner` Lambda (to be implemented) dispatches this command for assets whose recorded `StorageTier` lags the tier implied by their `CreatedAt` date.

---

## Alternatives Considered

**Keep tag-based rule, implement the tag-setting code**  
Rejected. Tags-on-archive means only explicitly archived objects tier down. The policy intent is that *all* originals follow the cost progression — archiving is a separate concern from storage cost management.

**Transition to Glacier Instant immediately on `AssetArchived`**  
Rejected. Archived assets may still be retrieved within the first year for compliance review or re-processing. Forcing Glacier Instant immediately adds retrieval friction and fees on a non-trivial access pattern.

**Intelligent-Tiering**  
Considered. S3 Intelligent-Tiering monitors access patterns and moves objects automatically. The monitoring fee ($0.0025/1,000 objects) makes it cost-ineffective for predictable, write-once-read-rarely media archives where the access pattern is known. Rejected in favour of an explicit deterministic policy.
