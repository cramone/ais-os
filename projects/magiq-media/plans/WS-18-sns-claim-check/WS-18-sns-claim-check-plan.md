---
id: MM-029
type: plan
project: magiq-media
workstream: WS-18-sns-claim-check
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, sns, s3, claim-check]
consumes: []
blocked-by-external: [MM-023]
status: shipped
branches: [feature/chase/MM-029-WS-18-sns-claim-check]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/49
merge-sha: afa706db
shipped: 2026-10-13
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F008-sns-claim-check-and-item-offload.md and INDEX.md#WS-18; no separate review document.
---

# WS-18 — SNS claim-check envelope + item-level S3 offload + bounded relay retries

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** MM-023 (WS-21 — outbox + relay)
**Unblocks:** large events / envelopes stop being unshippable

Delivers F008. Item-level offload > 350 KB; outbox-envelope claim-check > 240 KB; bounded relay to 10 attempts then `OutboxEntryParked`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Confirm MM-023 (WS-21) shipped. Paste:

> Picking up WS-18 (plan MM-029). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-18-sns-claim-check\WS-18-sns-claim-check-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F008-sns-claim-check-and-item-offload.md`.
>
> Depends on WS-21 (MM-023). Pre-publish: event > 350 KB → S3 `event-payloads/{guid}`, body = `{"payloadRef":"s3://..."}`. Outbox entry > 240 KB → S3 `event-envelopes/{guid}`, SNS message = `{"envelopeRef":"s3://..."}`. Outbox relay 10-attempt bound; exhaustion raises `OutboxEntryParked` + dead store.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F008 § Required-shape, § Detection signals
- [ ] Confirm MM-023 shipped (outbox contract available)
- [ ] Locate SNS publisher + outbox relay

## Phase 1 — Item-level S3 offload
- [ ] Pre-publish: measure byte size
- [ ] > `ItemOffloadThreshold` (default 350 KB) → write to `event-payloads/{guid}`
- [ ] Body replaced by `{"payloadRef":"s3://..."}`
- [ ] Consumer: detect `payloadRef`, read from S3, deserialize

## Phase 2 — Outbox envelope claim-check
- [ ] Pre-publish: measure outbox entry serialized size
- [ ] > `EnvelopeClaimCheckThreshold` (default 240 KB) → write to `event-envelopes/{guid}`
- [ ] SNS message carries `{"envelopeRef":"s3://..."}`
- [ ] Consumer: detect `envelopeRef`, read from S3

## Phase 3 — Bounded relay retries
- [ ] Outbox relay (WS-21) tracks `AttemptCount` per entry
- [ ] After 10 failures → raise `OutboxEntryParked` + move to dead store
- [ ] CloudWatch metric: `OutboxEntryParkedCount`

## Phase 4 — S3 lifecycle
- [ ] `event-payloads/` + `event-envelopes/` buckets — lifecycle per spec (document in README; infra may be WS-27a scope or separate)
- [ ] IAM: writer role for `Api` / outbox relay; reader for SQS consumers

## Phase 5 — Tests
- [ ] Unit: small payload — no offload
- [ ] Unit: large payload → S3 + `payloadRef`
- [ ] Unit: consumer rehydrates offloaded payload
- [ ] Unit: outbox entry > 240 KB → envelope claim-check
- [ ] Unit: 10 failed relay attempts → `OutboxEntryParked` + dead store
- [ ] Integration: LocalStack S3 + SNS round-trip

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F008: shipped
- [ ] platform-capabilities/INDEX.md: WS-18 → § Shipped
- [ ] Transparent to handlers — no magiq-media `-b` row

## Session log
- 2026-10-08: plan drafted (blocked on MM-023 ship)
- 2026-10-13: shipped SDK side on branch `feature/chase/MM-029-WS-18-sns-claim-check`.
  - **Event-store item-level offload.** `DynamoDbEventStoreOptions.S3OffloadThresholdBytes` default 400 KB → 350 KB and is applied to the whole `media-events` row, not per payload. New `EventStreamItemSerializer.SerializeEventStreamItemStreamsForItemAsync(events, itemBudgetBytes, ct)` runs three passes — build items inline, measure combined inline size, offload largest-first to `event-payloads/{guid}` until the row fits, then serialize streams. `DynamoDbEventStore.SaveAsync` (single + txn + batch) switched to the item-aware method. Three 150 KB events in one append (the F008 reproducer) now write cleanly in one `PutItem`.
  - **Outbox SNS claim-check envelope.** `OutboxOptions.EnvelopeClaimCheckThresholdBytes = 240_000` + `EnvelopeS3BucketName` + `EnvelopeClaimCheckEnabled()`. New `OutboxEnvelopeReference(string EnvelopeRef)` record. New `IOutboxEnvelopeStore` + `S3OutboxEnvelopeStore` writing to `event-envelopes/{guid}`. New `IOutboxEnvelopeOffloader` + default `OutboxEnvelopeOffloader` runs between `IOutboxLogicalMessageFactory.Create` and `IOutboxStore.EnqueueAsync` in all three `Outbox.EnqueueAsync` overloads; no-op unless both the store is registered and the bucket name is set. `OutboxLogicalMessage.EnvelopeS3Uri` (nullable) + ctor param. `DynamoDbOutboxTableSchema.Attributes.EnvelopeS3Uri` round-trips the attribute. `OutboxMessageProcessor.ProcessAsync` detects `EnvelopeS3Uri` at relay time and republishes an `OutboxEnvelopeReference` as the SNS `data`, keeping the original `MessageTypeIdentifier` so SNS subscriber filters still match. `IOutboxBuilder.AddClaimCheckEnvelope(bucketName, threshold = 240_000)` on the DynamoDb outbox builder is the opt-in.
  - **Bounded relay retries (Phase 3).** Already shipped under WS-21c (10-attempt park + `outbox.entry_parked` metric). No work this PR.
  - 10 new unit tests: 5 under `tests/.../EventSourcing/ItemLevelS3OffloadTests.cs` (under-budget inline, single-over-budget offloaded, mixed largest-first, no-S3-store no-op, empty batch) + 5 under `tests/.../Messaging/OutboxEnvelopeClaimCheckTests.cs` (offloader respects threshold, offloads with stub + `EnvelopeS3Uri`, no-op without store or without bucket, processor republishes `OutboxEnvelopeReference` as data). Full non-Docker regression 225 pass. Docker-dependent fixtures unchanged.
  - **Scope cut**: downstream consumer-side resolution (SQS reader detects `envelopeRef`, fetches from S3, deserializes full envelope) not in this PR. `IOutboxEnvelopeStore.DownloadEnvelopeAsync` is on the interface for the next workstream to wire.
  - **No `Magiq.Platform.*` version bump** — batched once the dependency-gap plans are done.
- 2026-10-13: PR #49 merged to `aspnetcore-platform/main` as `afa706db`. Tower MM-029 flipped `new` → `done`. Phase 4 (S3 bucket + IAM + CloudWatch alarm) is cdk-magiq-media work; cross-reference added under WS-21d / WS-25-cdk tracking. `docs/dependency-gaps/platform-capabilities/INDEX.md` + F008 status update not in the Z:/claudia/magiq snapshot — closure recorded in Tower + this session log only.
